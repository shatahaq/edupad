"""Sinkronkan data/corpus/chunks.jsonl ke tabel material_chunks di Supabase.

Hanya chunk baru/berubah yang di-embed; chunk yang hilang dari corpus dihapus.
"""

from __future__ import annotations

import hashlib
import json
import logging

from edupad.config import get_settings
from edupad.core.supabase import SupabaseClient, SupabaseError
from edupad.errors import EXIT_ERROR, EXIT_OK
from edupad.processing.corpus import CHUNKS_FILE
from edupad.processing.embeddings import EMBEDDING_MODEL, EmbeddingError, embed_passages

log = logging.getLogger(__name__)

TABLE = "material_chunks"
BATCH_SIZE = 32


def content_hash(chunk: dict) -> str:
    # Model ikut di-hash: ganti model = semua vektor dibuat ulang.
    return hashlib.sha256(f"{EMBEDDING_MODEL}\n{chunk['teks_embedding']}".encode()).hexdigest()


def to_row(chunk: dict, user_id: str, embedding: list[float]) -> dict:
    return {
        "user_id": user_id,
        "id": chunk["id"],
        "course_id": chunk["course_id"],
        "course_name": chunk["matkul"],
        "course_code": chunk["kode"],
        "meetings": chunk["pertemuan"],
        "section": chunk["section"],
        "title": chunk["judul"],
        "kind": chunk["jenis"],
        "location": chunk["lokasi"],
        "is_ocr": chunk["ocr"],
        "source_file": chunk["sumber_file"],
        "source_url": chunk["sumber_url"],
        "also_in": chunk["juga_di"],
        "word_count": chunk["kata"],
        "content": chunk["teks"],
        "content_hash": content_hash(chunk),
        "embedding_model": EMBEDDING_MODEL,
        "embedding": embedding,
    }


def load_chunks() -> list[dict]:
    if not CHUNKS_FILE.exists():
        return []
    with CHUNKS_FILE.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def run(force: bool = False) -> int:
    settings = get_settings()
    chunks = load_chunks()
    if not chunks:
        log.error("[x] %s kosong. Jalankan `python -m edupad corpus` dulu.", CHUNKS_FILE)
        return EXIT_ERROR
    try:
        db = SupabaseClient()
        user = f"eq.{settings.user_id}"
        existing = {} if force else {
            row["id"]: row["content_hash"] for row in db.select(TABLE, "id,content_hash", user_id=user)}

        pending = [c for c in chunks if existing.get(c["id"]) != content_hash(c)]
        for start in range(0, len(pending), BATCH_SIZE):
            batch = pending[start:start + BATCH_SIZE]
            vectors = embed_passages([c["teks_embedding"] for c in batch])
            db.upsert(TABLE, [to_row(c, settings.user_id, v) for c, v in zip(batch, vectors, strict=True)],
                      on_conflict="user_id,id")
            log.info("  %d/%d chunk di-embed & diunggah", start + len(batch), len(pending))

        current = {c["id"] for c in chunks}
        stale = sorted(set(existing) - current)
        for start in range(0, len(stale), 100):
            ids = ",".join(stale[start:start + 100])
            db.delete(TABLE, user_id=user, id=f"in.({ids})")
    except (SupabaseError, EmbeddingError) as e:
        log.error("[x] %s", e)
        return EXIT_ERROR

    log.info("[selesai] %d chunk: %d baru/berubah, %d tidak berubah, %d dihapus (model %s)",
             len(chunks), len(pending), len(chunks) - len(pending), len(stale), EMBEDDING_MODEL)
    return EXIT_OK
