"""Memory AI agent di Supabase: percakapan per sesi dan fakta jangka panjang pengguna.

Riwayat dikirim ke LLM dalam bentuk ringkas (suara, layar, sumber; tanpa detail
Markdown) dan hanya ditambah di belakang, sehingga prefix prompt tetap ter-cache.
Bila giliran yang belum diringkas mencapai SUMMARIZE_AFTER, giliran lama (selain
KEEP_TURNS terakhir) diringkas, dan fakta penting tentang pengguna ikut disimpan.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from datetime import datetime, timedelta

from edupad.config import WIB
from edupad.core.supabase import SupabaseClient

log = logging.getLogger(__name__)

SESSION_IDLE = timedelta(minutes=30)
KEEP_TURNS = 4
SUMMARIZE_AFTER = 8
MAX_FACTS = 30
MAX_SOURCES_PER_TURN = 4

SUMMARY_PROMPT = """Perbarui ringkasan percakapan antara mahasiswa dan asisten belajar EduPad.
Tulis JSON: {{"ringkasan": "...", "fakta_pengguna": ["..."]}}
- ringkasan: maks 120 kata; topik/mata kuliah/pertemuan yang dibahas, pertanyaan yang belum
  tuntas, dan rujukan yang mungkin ditanyakan lagi.
- fakta_pengguna: hal tentang mahasiswa yang berguna untuk sesi lain (kesulitan, preferensi cara
  belajar, target). Kosongkan bila tidak ada. Jangan masukkan isi materi.

RINGKASAN SEBELUMNYA:
{summary}

GILIRAN BARU:
{turns}"""


def format_sources(sources: list[dict]) -> str:
    seen, parts = set(), []
    for s in sources:
        key = (s["matkul"], tuple(s["pertemuan"]), s.get("judul"))
        if key in seen:
            continue
        seen.add(key)
        meetings = ", ".join(str(m) for m in s["pertemuan"])
        parts.append(f"{s['matkul']} p{meetings}: {s.get('judul') or '-'}")
    return "; ".join(parts[:MAX_SOURCES_PER_TURN])


def turn_messages(
    question: str, speech: str, screen: list[str], sources: list[dict], call_id: str = "riwayat"
) -> list[dict]:
    """Satu giliran untuk konteks LLM, ditulis sebagai panggilan tool `answer`.

    Bila ditulis sebagai teks biasa ("...Layar: ..."), model meniru format itu dan
    berhenti memanggil `answer`, sehingga daftar layar ikut dibacakan TTS.
    """
    arguments = json.dumps(
        {"speech": speech, "screen_lines": [line.lstrip("- ").strip() for line in screen]},
        ensure_ascii=False,
    )
    result = "ditampilkan ke pengguna" + (f"; sumber: {format_sources(sources)}" if sources else "")
    return [
        {"role": "user", "content": question},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": call_id,
                    "type": "function",
                    "function": {"name": "answer", "arguments": arguments},
                }
            ],
        },
        {"role": "tool", "tool_call_id": call_id, "content": result},
    ]


class ConversationMemory:
    def __init__(self, user_id: str, new_session: bool = False, db: SupabaseClient | None = None):
        self.user_id = user_id
        self.db = db or SupabaseClient()
        self.session = self._open_session(new_session)
        self._facts: list[str] | None = None
        self._prefetched: list[dict] | None = None

    def _open_session(self, new_session: bool) -> dict:
        if not new_session:
            rows = self.db.select(
                "agent_sessions",
                "*",
                user_id=f"eq.{self.user_id}",
                order="last_active.desc",
                limit="1",
            )
            if (
                rows
                and datetime.now(WIB) - datetime.fromisoformat(rows[0]["last_active"])
                < SESSION_IDLE
            ):
                return rows[0]
        return self.db.insert("agent_sessions", [{"user_id": self.user_id}])[0]

    def _turns(self) -> list[dict]:
        return self.db.select(
            "agent_turns",
            "id,question,speech,screen,sources",
            session_id=f"eq.{self.session['id']}",
            id=f"gt.{self.session['summarized_until']}",
            order="id.asc",
        )

    def prefetch(self) -> None:
        """Ambil fakta & riwayat sekarang (mis. paralel dengan STT); dipakai history() berikutnya."""
        self.facts()
        self._prefetched = self.history()

    def history(self) -> list[dict]:
        if self._prefetched is not None:
            messages, self._prefetched = self._prefetched, None
            return messages
        messages = []
        if self.session.get("summary"):
            messages.append(
                {
                    "role": "system",
                    "content": "Ringkasan percakapan sebelumnya di sesi ini: "
                    + self.session["summary"],
                }
            )
        for t in self._turns():
            messages += turn_messages(
                t["question"], t["speech"], t["screen"], t["sources"], call_id=f"riwayat_{t['id']}"
            )
        return messages

    def facts(self) -> list[str]:
        if self._facts is None:
            rows = self.db.select(
                "agent_memories",
                "content",
                user_id=f"eq.{self.user_id}",
                order="id.desc",
                limit=str(MAX_FACTS),
            )
            self._facts = [r["content"] for r in reversed(rows)]
        return self._facts

    def remember(self, fact: str) -> dict:
        fact = " ".join(fact.split())
        if not fact:
            return {"error": "fakta kosong"}
        if fact.lower() in (f.lower() for f in self.facts()):
            return {"status": "sudah diingat"}
        self.db.upsert(
            "agent_memories",
            [{"user_id": self.user_id, "content": fact}],
            on_conflict="user_id,content",
        )
        self.facts().append(fact)
        return {"status": "disimpan"}

    def save_turn(self, question: str, result: dict) -> None:
        self.db.insert(
            "agent_turns",
            [
                {
                    "session_id": self.session["id"],
                    "user_id": self.user_id,
                    "question": question,
                    "speech": result["speech"],
                    "screen": result["screen"]["lines"],
                    "detail": result["detail"],
                    "sources": result["sources"],
                    "usage": result["usage"],
                }
            ],
        )
        now = datetime.now(WIB).isoformat()
        self.db.update("agent_sessions", {"last_active": now}, id=f"eq.{self.session['id']}")
        self.session["last_active"] = now

    def maybe_summarize(self, complete: Callable[[str], str]) -> bool:
        """Ringkas giliran lama bila sudah banyak. `complete` = panggilan LLM teks -> JSON teks."""
        turns = self._turns()
        if len(turns) < SUMMARIZE_AFTER:
            return False
        old = turns[:-KEEP_TURNS]
        text = "\n".join(
            f"Mahasiswa: {t['question']}\nAsisten: {t['speech']}"
            + (f" (sumber: {format_sources(t['sources'])})" if t["sources"] else "")
            for t in old
        )
        data = json.loads(
            complete(SUMMARY_PROMPT.format(summary=self.session.get("summary") or "-", turns=text))
        )
        summary = (data.get("ringkasan") or "").strip()
        if not summary:
            return False
        self.db.update(
            "agent_sessions",
            {"summary": summary, "summarized_until": old[-1]["id"]},
            id=f"eq.{self.session['id']}",
        )
        self.session.update(summary=summary, summarized_until=old[-1]["id"])
        for fact in data.get("fakta_pengguna") or []:
            if isinstance(fact, str):
                self.remember(fact)
        log.info("[memory] %d giliran diringkas", len(old))
        return True

    def delete_user(self) -> None:
        """Hapus semua memory pengguna ini (dipakai evaluasi & permintaan pengguna)."""
        self.db.delete("agent_sessions", user_id=f"eq.{self.user_id}")
        self.db.delete("agent_memories", user_id=f"eq.{self.user_id}")
