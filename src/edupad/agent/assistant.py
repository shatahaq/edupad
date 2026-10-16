"""Loop agent: DeepSeek (API kompatibel OpenAI) + tool calling, tanpa framework.

Jawaban akhir selalu tiga bentuk: `speech` (TTS), `screen` (LCD), `detail` (Markdown).
"""

from __future__ import annotations

import functools
import json
import logging
import time
import uuid
from collections.abc import Callable
from datetime import datetime

import requests

from edupad.agent import coach, finance, tutor
from edupad.agent.formatting import clean_speech, fallback_answer, fit_screen
from edupad.agent.memory import ConversationMemory, turn_messages
from edupad.agent.tools import (
    ANSWER_TOOL,
    TOOLS,
    answer_schema,
    course_overview,
    resolve_course,
    tool_schemas,
)
from edupad.config import DEEPSEEK_URL, LOG_DIR, WIB, get_settings
from edupad.core import http_pool
from edupad.core.files import now_iso
from edupad.core.supabase import SupabaseError
from edupad.office.events import emit_status
from edupad.office.models import TOOL_AGENTS, AgentState

log = logging.getLogger(__name__)

LLM_TIMEOUT = 120
MAX_TOOL_RESULT_CHARS = 45_000
DAYS_ID = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
USAGE_LOG = LOG_DIR / "agent_usage.jsonl"
# USD per 1 juta token, tarif jam sibuk deepseek-flash (api-docs.deepseek.com, Okt 2026)
PRICE_PER_MTOK = {"cache_hit": 0.006, "cache_miss": 0.30, "output": 1.20}

SYSTEM_PROMPT = """Kamu EduPad, asisten belajar berbasis suara untuk mahasiswa D3 Teknik Informatika USU.
Pengguna bertanya lewat suara; jawabanmu dibacakan TTS dan ditampilkan di LCD kecil.

Cara kerja:
- Materi, tugas, presensi, dan jadwal: SELALU pakai tools atau data di bawah, jangan mengarang.
- Presensi/kehadiran -> get_attendance (sebut waktu "diperbarui" bila datanya bukan dari hari ini).
- Mata kuliah + nomor pertemuan disebut -> get_meeting (ringkasan; full=true bila perlu penjelasan
  rinci, contoh, atau kode). Topik/konsep -> search_materials.
  Tugas/deadline -> list_assignments. Daftar mata kuliah sudah ada di bawah, tidak perlu dicari.
- Hasil search_materials sudah diurutkan dari yang paling relevan; satu pencarian biasanya cukup.
  Cari lagi hanya bila hasilnya jelas tidak menjawab, dengan kata kunci yang berbeda.
  Hasil bertanda "sama dengan hasil sebelumnya" isinya sudah kamu terima.
- Teks bertanda OCR bisa salah baca; perbaiki seperlunya.
- Nama mata kuliah, nomor pertemuan, angka, dan tahun harus persis seperti di hasil tool yang
  kamu pakai; sebut sumber dari field matkul & pertemuan hasil tersebut.
- Selesaikan dengan memanggil tool `answer` tepat sekali:
  * speech: gaya bicara santai, maksimal 3 kalimat (~50 kata), langsung ke inti. Tanpa Markdown,
    simbol, kode, atau URL. Jangan membacakan perhitungan, daftar panjang, atau angka rinci:
    sebut gambaran besarnya, lalu arahkan ke layar. Jangan menjanjikan "ada tiga hal" lalu
    hanya menyebut satu. Sebut sumber singkat ("dari materi Pemrograman Visual pertemuan lima").
  * screen_title + screen_lines: poin kunci yang ringkas untuk LCD, tanpa emoji.
{detail_rule}
- Bila materi tidak ditemukan, katakan terus terang, jangan mengarang.

Hari ini: {today}.

Mata kuliah mahasiswa:
{courses}"""

MEMORY_PROMPT = """

Memory:
- Percakapan sebelumnya di sesi ini ada di riwayat; pakai untuk memahami pertanyaan lanjutan.
  "Sumber" di riwayat menunjukkan materi yang dibahas; ambil lagi isinya bila perlu detail.
- Bila mahasiswa menyebut hal tentang dirinya yang berguna di sesi lain (kesulitan, preferensi
  belajar, target) atau meminta diingat, panggil remember.
Catatan tentang mahasiswa ini:
{facts}"""

REMEMBER_TOOL = "remember"
REMEMBER_SCHEMA = {
    "type": "function",
    "function": {
        "name": REMEMBER_TOOL,
        "description": "Simpan fakta singkat tentang mahasiswa untuk sesi berikutnya.",
        "parameters": {
            "type": "object",
            "properties": {
                "fact": {
                    "type": "string",
                    "description": "satu kalimat, mis. 'Masih bingung operator logika'",
                }
            },
            "required": ["fact"],
        },
    },
}


class LLMError(RuntimeError):
    pass


def _system_prompt(memory: ConversationMemory | None = None, with_detail: bool = True) -> str:
    now = datetime.now(WIB)
    today = f"{DAYS_ID[now.weekday()]}, {now:%d-%m-%Y}"  # per hari agar prefix prompt ter-cache
    detail_rule = (
        "  * detail: jawaban lengkap Markdown + sumber (judul materi, pertemuan, URL)."
        if with_detail
        else "  * Tidak perlu jawaban panjang; layar dan suara sudah cukup."
    )
    prompt = SYSTEM_PROMPT.format(today=today, courses=course_overview(), detail_rule=detail_rule)
    prompt += tutor.TUTOR_RULES
    if memory:
        prompt += MEMORY_PROMPT.format(facts="\n".join(f"- {f}" for f in memory.facts()) or "-")
    return prompt


def _chat(messages: list[dict], tools: list[dict] | None = None, json_mode: bool = False) -> dict:
    settings = get_settings()
    if not settings.llm_api_key:
        raise LLMError("API_KEY_AI belum diisi di .env")
    payload = {
        "model": settings.llm_model,
        "messages": messages,
        "reasoning_effort": settings.llm_effort,
    }
    if settings.llm_max_output_tokens:
        payload["max_tokens"] = settings.llm_max_output_tokens
    if tools:
        payload.update(tools=tools, tool_choice="auto")
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    try:
        response = http_pool.post(
            f"{DEEPSEEK_URL}/chat/completions",
            json=payload,
            timeout=LLM_TIMEOUT,
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
        )
    except requests.RequestException as e:
        raise LLMError(f"DeepSeek tidak bisa dihubungi: {e}") from e
    if not response.ok:
        raise LLMError(f"HTTP {response.status_code}: {response.text[:300]}")
    return response.json()


def _run_tool(name: str, raw_args: str) -> dict:
    try:
        args = json.loads(raw_args or "{}")
        return TOOLS[name](**args)
    except Exception as e:  # noqa: BLE001 - error dikembalikan ke LLM agar bisa mencoba lagi
        return {"error": f"{type(e).__name__}: {e}"}


SEEN_NOTE = "(sama dengan hasil sebelumnya)"


def dedupe(name: str, result: dict, seen: set) -> dict:
    """Potongan materi yang sudah ada di konteks percakapan ini tidak dikirim ulang."""
    if name == "get_meeting" and "isi" in result:
        key = ("meeting", result["matkul"], result["pertemuan"])
        if key in seen:
            return {**result, "isi": SEEN_NOTE}
        seen.add(key)
    if name != "search_materials":
        return result
    rows = []
    for row in result.get("hasil", []):
        if row["id"] in seen or any(
            ("meeting", row["matkul"], m) in seen for m in row["pertemuan"]
        ):
            rows.append(
                {k: row[k] for k in ("id", "matkul", "pertemuan", "judul")} | {"isi": SEEN_NOTE}
            )
        else:
            seen.add(row["id"])
            rows.append(row)
    return {**result, "hasil": rows}


def _sources(result: dict) -> list[dict]:
    """(mata kuliah, pertemuan, judul) yang dilihat model dari satu hasil tool."""
    rows = result.get("hasil") or ([result] if "pertemuan" in result and "matkul" in result else [])
    sources = []
    for row in rows:
        course = resolve_course(row["matkul"])
        meetings = row["pertemuan"] if isinstance(row["pertemuan"], list) else [row["pertemuan"]]
        sources.append(
            {
                "course_id": course["course_id"] if course else None,
                "matkul": row["matkul"],
                "pertemuan": meetings,
                "judul": row.get("judul") or row.get("judul_section"),
            }
        )
    return sources


class Usage:
    """Token per panggilan LLM; token cache jauh lebih murah, jadi dicatat terpisah."""

    def __init__(self):
        self.calls, self.cache_hit, self.cache_miss, self.output, self.reasoning = 0, 0, 0, 0, 0

    def add(self, usage: dict) -> None:
        self.calls += 1
        hit = usage.get("prompt_cache_hit_tokens", 0)
        self.cache_hit += hit
        self.cache_miss += usage.get(
            "prompt_cache_miss_tokens", usage.get("prompt_tokens", 0) - hit
        )
        self.output += usage.get("completion_tokens", 0)
        self.reasoning += (usage.get("completion_tokens_details") or {}).get("reasoning_tokens", 0)

    @property
    def total(self) -> int:
        return self.cache_hit + self.cache_miss + self.output

    @property
    def cost_usd(self) -> float:
        return (
            self.cache_hit * PRICE_PER_MTOK["cache_hit"]
            + self.cache_miss * PRICE_PER_MTOK["cache_miss"]
            + self.output * PRICE_PER_MTOK["output"]
        ) / 1e6

    def as_dict(self) -> dict:
        return {
            "calls": self.calls,
            "total": self.total,
            "cache_hit": self.cache_hit,
            "cache_miss": self.cache_miss,
            "output": self.output,
            "reasoning": self.reasoning,
            "cost_usd": round(self.cost_usd, 6),
        }


def _remember(memory: ConversationMemory, raw_args: str) -> dict:
    try:
        return memory.remember(json.loads(raw_args or "{}").get("fact", ""))
    except (SupabaseError, json.JSONDecodeError) as e:
        return {"error": str(e)}


def _save_turn(memory: ConversationMemory, question: str, result: dict) -> None:
    try:
        memory.save_turn(question, result)
        memory.maybe_summarize(_complete_json)
    except (SupabaseError, LLMError, ValueError, KeyError) as e:
        log.warning("[!] giliran tidak tersimpan ke memory: %s", e)


def _run_now(job: Callable[[], None]) -> None:
    job()


def _log_usage(question: str, result: dict) -> None:
    entry = {
        "waktu": now_iso(),
        "pertanyaan": question,
        "tools": [t["tool"] for t in result["tools"]],
        "detik": result["seconds"],
        **result["usage"],
    }
    try:
        USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
        with USAGE_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as e:
        log.warning("[!] gagal mencatat pemakaian token: %s", e)


def _final(raw_args: str) -> dict:
    try:
        args = json.loads(raw_args or "{}")
    except json.JSONDecodeError:
        return fallback_answer(raw_args)
    detail = (args.get("detail") or "").strip()
    return {
        "speech": clean_speech(args.get("speech") or detail),
        "screen": fit_screen(args.get("screen_title") or "EduPad", args.get("screen_lines") or []),
        "detail": detail,
    }


def _complete_json(prompt: str) -> str:
    reply = _chat([{"role": "user", "content": prompt}], json_mode=True)
    return reply["choices"][0]["message"]["content"]


def open_memory(user_id: str | None = None, new_session: bool = False) -> ConversationMemory | None:
    """Memory Supabase; None (agent tetap jalan tanpa memory) bila Supabase tidak bisa dipakai."""
    try:
        return ConversationMemory(user_id or get_settings().user_id, new_session=new_session)
    except SupabaseError as e:
        log.warning("[!] memory tidak tersedia: %s", e)
        return None


def ask(
    question: str,
    history: list[dict] | None = None,
    memory: ConversationMemory | None = None,
    with_detail: bool = False,
    defer_save: Callable[[Callable[[], None]], object] | None = None,
) -> dict:
    """Jawab satu pertanyaan.

    Konteks percakapan diambil dari `memory` (Supabase, bertahan antar proses) atau dari
    `history` (pesan dari pemanggilan sebelumnya). `history` baru ikut dikembalikan.
    Default mode perangkat (suara + LCD); `with_detail=True` menambah jawaban Markdown lengkap.
    `defer_save` (mis. executor.submit) menerima penyimpanan giliran ke memory agar jawaban
    tidak menunggu Supabase; tanpa itu giliran disimpan sebelum ask() kembali.
    """
    office_run_id = f"ask-{uuid.uuid4().hex[:12]}"
    emit_status(
        "tutor",
        AgentState.RUNNING,
        room="tutor-room",
        job_type="ask",
        message="Memahami pertanyaan mahasiswa",
        progress=5,
        run_id=office_run_id,
    )
    if memory:
        history = memory.history()
    history = list(history or [])
    schemas = [
        *tool_schemas(),
        *tutor.SCHEMAS,
        *coach.SCHEMAS,
        *finance.SCHEMAS,
        answer_schema(with_detail),
        *([REMEMBER_SCHEMA] if memory else []),
    ]
    quiz_note = tutor.context_note(getattr(memory, "user_id", None))
    messages = [
        {"role": "system", "content": _system_prompt(memory, with_detail)},
        *history,
        # Kuis yang sedang berjalan: setelah riwayat agar awalan prompt tetap ter-cache.
        *([{"role": "system", "content": quiz_note}] if quiz_note else []),
        {"role": "user", "content": question},
    ]
    trace, sources, usage, seen, nudged = [], [], Usage(), set(), False
    started = time.time()
    max_tool_rounds = get_settings().llm_max_tool_rounds

    for _ in range(max_tool_rounds + 1):
        try:
            reply = _chat(messages, schemas)
        except Exception:
            emit_status(
                "tutor",
                AgentState.FAILED,
                room="tutor-room",
                job_type="ask",
                message="Permintaan tutor gagal diproses",
                progress=100,
                run_id=office_run_id,
            )
            raise
        usage.add(reply.get("usage", {}))
        message = reply["choices"][0]["message"]
        calls = message.get("tool_calls") or []

        final_call = next((c for c in calls if c["function"]["name"] == ANSWER_TOOL), None)
        if not final_call and not calls and not nudged:
            nudged = True  # model menjawab dengan teks biasa; minta lewat `answer` agar suara & layar terpisah
            messages += [
                {"role": "assistant", "content": message.get("content") or ""},
                {"role": "user", "content": "Sampaikan jawaban itu dengan memanggil tool answer."},
            ]
            continue
        if final_call or not calls:
            answer = (
                _final(final_call["function"]["arguments"])
                if final_call
                else fallback_answer(message.get("content") or "")
            )
            history += turn_messages(
                question,
                answer["speech"],
                answer["screen"]["lines"],
                sources,
                call_id=f"riwayat_{len(history)}",
            )
            result = {
                **answer,
                "tools": trace,
                "sources": sources,
                "usage": usage.as_dict(),
                "tokens": usage.total,
                "cached_tokens": usage.cache_hit,
                "seconds": round(time.time() - started, 1),
                "history": history,
            }
            _log_usage(question, result)
            if memory:
                (defer_save or _run_now)(functools.partial(_save_turn, memory, question, result))
            emit_status(
                "tutor",
                AgentState.SUCCEEDED,
                room="tutor-room",
                job_type="ask",
                message="Jawaban siap ditampilkan",
                progress=100,
                run_id=office_run_id,
                metadata={"seconds": result["seconds"], "tools": [t["tool"] for t in trace]},
            )
            return result

        messages.append(message)
        for call in calls:
            name, args = call["function"]["name"], call["function"]["arguments"]
            tool_agent, tool_room = TOOL_AGENTS.get(name, ("tutor", "tutor-room"))
            emit_status(
                tool_agent,
                AgentState.RUNNING,
                room=tool_room,
                job_type=name,
                message=f"Menjalankan {name.replace('_', ' ')}",
                progress=min(25 + len(trace) * 15, 85),
                run_id=office_run_id,
            )
            tool_started = time.time()
            if name == REMEMBER_TOOL and memory:
                result = _remember(memory, args)
            else:
                result = dedupe(name, _run_tool(name, args), seen)
            sources += _sources(result)
            output = json.dumps(result, ensure_ascii=False)[:MAX_TOOL_RESULT_CHARS]
            trace.append(
                {
                    "tool": name,
                    "args": args,
                    "ms": int((time.time() - tool_started) * 1000),
                    "error": output.startswith('{"error"'),
                    "output": output,
                }
            )
            tool_failed = output.startswith('{"error"')
            emit_status(
                tool_agent,
                AgentState.FAILED if tool_failed else AgentState.SUCCEEDED,
                room=tool_room,
                job_type=name,
                message=(
                    f"{name.replace('_', ' ').capitalize()} perlu diperiksa"
                    if tool_failed
                    else f"{name.replace('_', ' ').capitalize()} selesai"
                ),
                progress=100,
                run_id=office_run_id,
            )
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": output})
    emit_status(
        "tutor",
        AgentState.FAILED,
        room="tutor-room",
        job_type="ask",
        message="Agent melewati batas putaran tool",
        progress=100,
        run_id=office_run_id,
    )
    raise LLMError(f"melebihi {max_tool_rounds} putaran tool tanpa jawaban akhir")
