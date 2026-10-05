"""Ringkasan per pertemuan untuk AI agent (data/corpus/summaries.json).

Dibuat sekali per isi materi (hash), sehingga pertanyaan "pertemuan N membahas apa"
cukup dijawab dari ringkasan tanpa mengirim seluruh materi ke LLM setiap kali.
"""

from __future__ import annotations

import hashlib
import json
import logging

import requests

from edupad.config import CORPUS_DIR, DEEPSEEK_URL, get_settings
from edupad.core.files import read_json, write_json
from edupad.errors import EXIT_ERROR, EXIT_OK

log = logging.getLogger(__name__)

SUMMARIES_FILE = CORPUS_DIR / "summaries.json"
CATALOG_FILE = CORPUS_DIR / "catalog.json"
PROMPT_VERSION = 1
MAX_INPUT_CHARS = 60_000

PROMPT = """Ringkas materi kuliah berikut untuk asisten belajar mahasiswa.
Tulis JSON: {{"ringkasan": "...", "topik": ["..."], "ada_contoh_kode": true/false}}
- ringkasan: 120-200 kata, bahasa Indonesia, inti konsep dan poin penting sesuai materi.
  Jangan menambah hal yang tidak ada di materi.
- topik: 4-10 subtopik/judul bagian yang dibahas, singkat.
- ada_contoh_kode: apakah materi memuat contoh kode program.

MATERI ({course}, pertemuan {meeting}):
{text}"""


def _hash(text: str, model: str) -> str:
    return hashlib.sha256(f"{PROMPT_VERSION}\n{model}\n{text}".encode()).hexdigest()


def summarize_text(course: str, meeting: str, text: str) -> dict:
    settings = get_settings()
    response = requests.post(
        f"{DEEPSEEK_URL}/chat/completions", timeout=180,
        headers={"Authorization": f"Bearer {settings.llm_api_key}"},
        json={"model": settings.llm_model, "response_format": {"type": "json_object"},
              "messages": [{"role": "user", "content": PROMPT.format(
                  course=course, meeting=meeting, text=text[:MAX_INPUT_CHARS])}]})
    response.raise_for_status()
    data = json.loads(response.json()["choices"][0]["message"]["content"])
    return {"ringkasan": str(data.get("ringkasan") or "").strip(),
            "topik": [str(t) for t in data.get("topik") or []],
            "ada_contoh_kode": bool(data.get("ada_contoh_kode"))}


def get_summary(course_id: str, meeting: str) -> dict | None:
    return read_json(SUMMARIES_FILE).get(course_id, {}).get(meeting)


def run(force: bool = False) -> int:
    settings = get_settings()
    if not settings.llm_api_key:
        log.error("[x] API_KEY_AI belum diisi di .env")
        return EXIT_ERROR
    catalog = read_json(CATALOG_FILE).get("mata_kuliah", [])
    old = {} if force else read_json(SUMMARIES_FILE)
    new: dict = {}
    made = kept = failed = 0
    for course in catalog:
        for meeting, entry in course["pertemuan"].items():
            text = (CORPUS_DIR / entry["file"]).read_text(encoding="utf-8")
            digest = _hash(text, settings.llm_model)
            previous = old.get(course["course_id"], {}).get(meeting)
            if previous and previous.get("hash") == digest:
                new.setdefault(course["course_id"], {})[meeting] = previous
                kept += 1
                continue
            try:
                summary = summarize_text(course["matkul"], meeting, text)
            except (requests.RequestException, ValueError, KeyError) as e:
                log.warning("[!] %s p%s: ringkasan gagal: %s", course["matkul"], meeting, e)
                if previous:  # ringkasan lama tetap lebih baik daripada tidak ada
                    new.setdefault(course["course_id"], {})[meeting] = previous
                failed += 1
                continue
            new.setdefault(course["course_id"], {})[meeting] = {"hash": digest, **summary}
            made += 1
            log.info("  [ringkas] %s p%s", course["matkul"], meeting)
    write_json(SUMMARIES_FILE, new)
    log.info("[selesai] ringkasan pertemuan: %d dibuat, %d tidak berubah, %d gagal", made, kept, failed)
    return EXIT_ERROR if failed else EXIT_OK
