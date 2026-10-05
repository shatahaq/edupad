"""Evaluasi AI agent: biaya token & kualitas jawaban pada set uji evals/agent_cases.json.

Tiap jawaban diperiksa tiga cara: sumber yang terambil, kata kunci wajib, dan
penilaian model yang lebih kuat (LLM-as-judge) terhadap materi aslinya.
"""

from __future__ import annotations

import json
import logging
import re
import statistics
import time
import uuid
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import requests

from edupad.agent import tools
from edupad.config import BASE_DIR, CORPUS_DIR, DEEPSEEK_URL, WIB, get_settings
from edupad.core.files import now_iso, write_json

log = logging.getLogger(__name__)

CASES_FILE = BASE_DIR / "evals" / "agent_cases.json"
RESULTS_DIR = BASE_DIR / "evals" / "results"
JUDGE_MODEL = "deepseek-flash"  # v4-pro ~4x lebih mahal; flash cukup dengan rujukan lengkap
MAX_REFERENCE_CHARS = 30_000
MAX_TOOL_DATA_CHARS = 30_000
NOT_FOUND = re.compile(r"belum (ada|punya|tersedia|ditemukan|menemukan)|tidak (ada|ditemukan|tersedia|menemukan)|"
                       r"tidak bisa menemukan|kosong", re.I)

JUDGE_PROMPT = """Kamu penilai jawaban asisten belajar berbasis suara untuk mahasiswa.
Jawaban terdiri dari SUARA (dibacakan, sengaja singkat), LAYAR (poin LCD), dan DETAIL
(teks lengkap; boleh kosong pada mode perangkat, jangan kurangi nilai karena itu).

Sumber kebenaran: MATERI RUJUKAN, DATA YANG DITERIMA ASISTEN (hasil tool), dan DATA MATA KULIAH.
Beri JSON:
{{"ketepatan": 1-5, "kelengkapan": 1-5, "halusinasi": true/false, "catatan": "maks 2 kalimat"}}
- ketepatan: isi benar menurut sumber kebenaran dan menjawab pertanyaan.
- kelengkapan: poin penting yang relevan dengan pertanyaan tercakup, sesuai porsi jawaban suara
  (SUARA+LAYAR untuk inti; DETAIL bila ada untuk rincian).
- halusinasi: true hanya bila ada klaim yang bertentangan dengan sumber kebenaran, atau mengarang
  isi materi/data yang tidak ada di sumber mana pun. Pengetahuan umum yang benar bukan halusinasi.
- Bila materi tidak tersedia, jawaban terbaik mengaku tidak ada (ketepatan 5) tanpa mengarang isi.

TANGGAL SAAT MENJAWAB: {today}

DATA MATA KULIAH:
{courses}

PERCAKAPAN SEBELUMNYA:
{context}

PERTANYAAN: {question}

MATERI RUJUKAN:
{reference}

DATA YANG DITERIMA ASISTEN:
{tool_data}

JAWABAN
SUARA: {speech}
LAYAR: {screen}
DETAIL: {detail}"""


def load_cases(ids: list[str] | None = None) -> list[dict]:
    cases = json.loads(CASES_FILE.read_text(encoding="utf-8"))["cases"]
    return [c for c in cases if not ids or c["id"] in ids]


def _meeting_text(course_id: str, meeting: int | None) -> str:
    course = next((c for c in tools._catalog() if c["course_id"] == course_id), None)
    if not course:
        return ""
    keys = [str(meeting)] if meeting is not None else [k for k in course["pertemuan"] if k != "umum"]
    parts = []
    for key in keys:
        entry = course["pertemuan"].get(key)
        if entry:
            parts.append(f"## {course['matkul']} pertemuan {key}\n"
                         + (CORPUS_DIR / entry["file"]).read_text(encoding="utf-8"))
    return "\n\n".join(parts)


def reference_for(expect: dict) -> str:
    if expect.get("not_found"):
        return "Materi untuk pertanyaan ini TIDAK tersedia di data mahasiswa."
    if "list_assignments" in expect.get("tools", []):
        return json.dumps(tools.list_assignments(only_pending=True), ensure_ascii=False)
    text = "\n\n".join(_meeting_text(c, m) for c, m in expect.get("sources", []))
    return text[:MAX_REFERENCE_CHARS] or "(tidak ada rujukan)"


def _matches(keyword: str, text: str) -> bool:
    return any(alt.strip().lower() in text for alt in keyword.split("|"))


def check_turn(expect: dict, result: dict) -> dict:
    answer = " ".join([result["speech"], " ".join(result["screen"]["lines"]), result["detail"]]).lower()
    checks: dict = {}
    if expect.get("sources"):
        got = {(s["course_id"], m) for s in result["sources"] for m in s["pertemuan"]}
        checks["sumber"] = all(any(c == course and (meeting is None or m == meeting) for c, m in got)
                               for course, meeting in expect["sources"])
    if expect.get("keywords"):
        hits = [_matches(k, answer) for k in expect["keywords"]]
        checks["kata_kunci"] = sum(hits) / len(hits)
    if expect.get("tools"):
        used = {t["tool"] for t in result["tools"]}
        checks["tools"] = all(t in used for t in expect["tools"])
    if expect.get("not_found"):
        checks["mengaku_tidak_ada"] = bool(NOT_FOUND.search(result["speech"]))
    return checks


def judge(question: str, context: str, expect: dict, row: dict) -> dict:
    settings = get_settings()
    tool_data = "\n\n".join(row.get("konteks") or [])[:MAX_TOOL_DATA_CHARS] or "(tidak memanggil tool)"
    prompt = JUDGE_PROMPT.format(
        today=row.get("tanggal", "-"), courses=tools.course_overview(), context=context or "-",
        question=question, reference=reference_for(expect), tool_data=tool_data,
        speech=row["speech"], screen=" | ".join(row["screen"]), detail=row["detail"] or "(kosong)")
    for attempt in range(3):
        try:
            response = requests.post(
                f"{DEEPSEEK_URL}/chat/completions", timeout=180,
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json={"model": JUDGE_MODEL, "messages": [{"role": "user", "content": prompt}],
                      "response_format": {"type": "json_object"}})
            response.raise_for_status()
            body = response.json()
            verdict = json.loads(body["choices"][0]["message"]["content"])
            verdict["usage"] = body.get("usage", {})
            return verdict
        except (requests.RequestException, ValueError, KeyError) as e:
            error = str(e)
            time.sleep(2 ** attempt)
    return {"error": error}


def run_case(case: dict, ask_turn: Callable[[str, dict], dict], use_judge: bool,
             state: dict | None = None) -> list[dict]:
    state = {} if state is None else state
    context: list[str] = []
    rows = []
    for turn in case["turns"]:
        result = ask_turn(turn["q"], state)
        row = {"case": case["id"], "q": turn["q"], "tanggal": _today(), "speech": result["speech"],
               "screen": result["screen"]["lines"], "detail": result["detail"],
               "tools": [f"{t['tool']}({t['args']})" for t in result["tools"]],
               "konteks": [f"{t['tool']}({t['args']}) -> {t['output']}" for t in result["tools"]],
               "sources": result["sources"], "seconds": result["seconds"], "usage": result["usage"],
               "checks": check_turn(turn["expect"], result)}
        if use_judge:
            row["judge"] = judge(turn["q"], "\n".join(context), turn["expect"], row)
        context += [f"Pengguna: {turn['q']}", f"Asisten: {result['speech']}"]
        rows.append(row)
        log.info("  %-24s %5d tok  $%.5f  %4.1fs  %s  %s", case["id"], result["usage"]["total"],
                 result["usage"]["cost_usd"], result["seconds"], row["checks"],
                 {k: row.get("judge", {}).get(k) for k in ("ketepatan", "kelengkapan", "halusinasi")})
    return rows


def summarize(rows: list[dict]) -> dict:
    def mean(values: list[float]) -> float | None:
        return round(statistics.mean(values), 3) if values else None

    judged = [r["judge"] for r in rows if "judge" in r and "error" not in r["judge"]]
    check = lambda key: [float(r["checks"][key]) for r in rows if key in r["checks"]]  # noqa: E731
    return {
        "jawaban": len(rows),
        "token_per_jawaban": mean([r["usage"]["total"] for r in rows]),
        "token_miss_per_jawaban": mean([r["usage"]["cache_miss"] for r in rows]),
        "output_per_jawaban": mean([r["usage"]["output"] for r in rows]),
        "panggilan_llm_per_jawaban": mean([r["usage"]["calls"] for r in rows]),
        "biaya_usd_per_jawaban": round(statistics.mean([r["usage"]["cost_usd"] for r in rows]), 6),
        "detik_per_jawaban": mean([r["seconds"] for r in rows]),
        "sumber_tepat": mean(check("sumber")),
        "kata_kunci": mean(check("kata_kunci")),
        "tools_tepat": mean(check("tools")),
        "mengaku_tidak_ada": mean(check("mengaku_tidak_ada")),
        "judge_ketepatan": mean([j["ketepatan"] for j in judged]),
        "judge_kelengkapan": mean([j["kelengkapan"] for j in judged]),
        "halusinasi": sum(bool(j.get("halusinasi")) for j in judged),
        "token_judge_total": sum(j.get("usage", {}).get("total_tokens", 0) for j in judged),
    }


def _today() -> str:
    from edupad.agent.assistant import DAYS_ID

    now = datetime.now(WIB)
    return f"{DAYS_ID[now.weekday()]}, {now:%d-%m-%Y %H:%M} WIB"


def make_ask_turn(use_memory: bool, with_detail: bool) -> Callable[[str, dict], dict]:
    """Tanpa memory: riwayat diteruskan di RAM. Dengan memory: tiap giliran membuka memory
    Supabase dari awal (seperti proses baru), dengan user khusus per kasus."""
    from edupad.agent.assistant import ask, open_memory

    def ask_turn(question: str, state: dict) -> dict:
        if not use_memory:
            result = ask(question, state.get("history"), with_detail=with_detail)
            state["history"] = result["history"]
            return result
        first = "user" not in state
        state.setdefault("user", f"eval-{uuid.uuid4().hex[:12]}")
        memory = open_memory(state["user"], new_session=first)
        if memory is None:
            raise RuntimeError("memory Supabase tidak tersedia")
        state["memory"] = memory
        return ask(question, memory=memory, with_detail=with_detail)

    return ask_turn


def run(label: str, case_ids: list[str] | None = None, repeat: int = 1, use_judge: bool = True,
        use_memory: bool = True, with_detail: bool = False, summaries: bool = True) -> Path:
    tools.USE_MEETING_SUMMARIES = summaries
    ask_turn = make_ask_turn(use_memory, with_detail)
    cases = load_cases(case_ids)
    rows = []
    for i in range(repeat):
        log.info("[..] %s: putaran %d/%d, %d kasus", label, i + 1, repeat, len(cases))
        for case in cases:
            state: dict = {}
            try:
                rows += run_case(case, ask_turn, use_judge, state)
            finally:
                if state.get("memory"):
                    state["memory"].delete_user()
    summary = summarize(rows)
    path = RESULTS_DIR / f"{label}.json"
    config = {"memory": use_memory, "detail": with_detail, "ringkasan_pertemuan": summaries}
    write_json(path, {"label": label, "waktu": now_iso(), "konfigurasi": config, "ringkasan": summary,
                      "jawaban": rows})
    log.info("[selesai] %s -> %s", json.dumps(summary, ensure_ascii=False), path)
    return path


def rejudge(label: str) -> Path:
    """Nilai ulang hasil tersimpan (cek & judge) tanpa menanyai agent lagi."""
    path = RESULTS_DIR / f"{label}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = {c["id"]: c for c in load_cases()}
    turn_index: dict[str, int] = {}
    context: dict[str, list[str]] = {}
    for row in data["jawaban"]:
        i = turn_index.get(row["case"], 0)
        if i == 0:
            context[row["case"]] = []
        expect = cases[row["case"]]["turns"][i]["expect"]
        result = {"speech": row["speech"], "screen": {"lines": row["screen"]}, "detail": row["detail"],
                  "sources": row.get("sources", []),
                  "tools": [{"tool": t.split("(", 1)[0]} for t in row["tools"]]}
        row["checks"] = check_turn(expect, result)
        row["judge"] = judge(row["q"], "\n".join(context[row["case"]]), expect, row)
        context[row["case"]] += [f"Pengguna: {row['q']}", f"Asisten: {row['speech']}"]
        turn_index[row["case"]] = (i + 1) % len(cases[row["case"]]["turns"])
        log.info("  %-24s %s %s", row["case"], row["checks"],
                 {k: row["judge"].get(k) for k in ("ketepatan", "kelengkapan", "halusinasi")})
    data["ringkasan"] = summarize(data["jawaban"])
    write_json(path, data)
    log.info("[selesai] %s", json.dumps(data["ringkasan"], ensure_ascii=False))
    return path


def compare(labels: list[str]) -> str:
    summaries = {lb: json.loads((RESULTS_DIR / f"{lb}.json").read_text(encoding="utf-8"))["ringkasan"]
                 for lb in labels}
    keys = list(next(iter(summaries.values())))
    width = max(len(lb) for lb in labels) + 2
    lines = ["metrik".ljust(28) + "".join(lb.rjust(width) for lb in labels)]
    lines += [k.ljust(28) + "".join(str(summaries[lb].get(k, "-")).rjust(width) for lb in labels) for k in keys]
    return "\n".join(lines)
