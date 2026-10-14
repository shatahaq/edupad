"""Riwayat percakapan perangkat untuk dashboard Office.

Data tetap dibaca dari tabel ``agent_turns`` yang sudah dipakai AI agent. Modul
ini sengaja hanya mengembalikan kolom presentasi yang aman; detail tool, usage,
dan kredensial tidak pernah dikirim ke frontend.
"""

from __future__ import annotations

from edupad.config import get_settings
from edupad.core.supabase import SupabaseClient


def list_recent_iot_chats(
    limit: int = 12,
    *,
    db: SupabaseClient | None = None,
    user_id: str | None = None,
) -> list[dict]:
    """Ambil percakapan IoT terbaru untuk pengguna EduPad aktif."""
    safe_limit = max(1, min(limit, 50))
    owner = user_id or get_settings().user_id
    client = db or SupabaseClient()
    rows = client.select(
        "agent_turns",
        "id,session_id,question,speech,screen,created_at",
        user_id=f"eq.{owner}",
        order="created_at.desc",
        limit=str(safe_limit),
    )
    return [
        {
            "id": row["id"],
            "session_id": row.get("session_id"),
            "question": row.get("question") or "",
            "answer": row.get("speech") or "",
            "screen": row.get("screen") or [],
            "created_at": row.get("created_at"),
        }
        for row in rows
    ]
