"""Bahasa EduPad: Indonesia (bawaan) atau Inggris.

Satu setelan mengubah semua yang didengar dan dibaca mahasiswa: bahasa pengenalan suara
(voice/stt.py), bahasa suara TTS (voice/tts.py), bahasa jawaban agent (agent/assistant.py), dan
kalimat tetap yang suaranya sudah disimpan (voice/clips.py, voice/commands.py, voice/intro.py).

Kalimat tetap ditulis dua bahasa sebagai {"id": ..., "en": ...} lalu dipilih lewat pick().
Kunci simpanan suara ikut teksnya (clips.version), jadi berganti bahasa membuat perangkat
mengunduh ulang pesan status, dan suara bahasa sebelumnya tetap tersimpan: berpindah bolak-balik
tidak memakai kuota TTS lagi.

Setelan di data/device/language.json; diubah lewat suara ("switch to English", "ganti ke bahasa
Indonesia" - ditangani voice/commands.py tanpa LLM), tool set_language, atau dashboard.
"""

from __future__ import annotations

import logging
import threading

from edupad.config import DATA_DIR
from edupad.core.files import now_iso, read_json, write_json

log = logging.getLogger(__name__)

SETTINGS_FILE = DATA_DIR / "device" / "language.json"
# `tts` dikirim ke ElevenLabs (language_code), `stt` ke Whisper (language).
LANGUAGES = {
    "id": {"label": "Indonesia", "tts": "id", "stt": "id"},
    "en": {"label": "English", "tts": "en", "stt": "en"},
}
DEFAULT = "id"
# Nama yang dipakai saat bicara/menulis, mis. konfirmasi "Bahasa Inggris aktif".
NAMES = {
    "id": {"id": "bahasa Indonesia", "en": "Indonesian"},
    "en": {"id": "bahasa Inggris", "en": "English"},
}

_lock = threading.Lock()

# Selalu ada di system prompt: cara berganti bahasa lewat suara.
PROMPT_RULE = """
- "Ganti ke bahasa Inggris" / "switch to English" (atau sebaliknya) -> set_language, lalu
  konfirmasi singkat dalam bahasa yang baru."""

# Ditambahkan saat bahasa Inggris aktif. Prompt utama tetap bahasa Indonesia (dan tetap ter-cache);
# yang diubah hanya bahasa keluaran untuk mahasiswa.
ENGLISH_RULES = """

ENGLISH MODE: this student uses EduPad in English. Everything the student hears or reads must be
in English - speech, screen_title, screen_lines, and detail - even though these instructions, the
tool results, and the course material are in Indonesian.
- Course names, lecturer names, and file titles stay exactly as the tools return them
  ("Pemrograman Visual, meeting five"); do not translate or invent English titles.
- Days, dates, and times in English ("Thursday at nine p.m."); keep the numbers themselves.
- Indonesian material is explained in English, not translated word for word.
- If the student speaks Indonesian, answer in English anyway and say that "ganti ke bahasa
  Indonesia" switches back."""


def load() -> dict:
    data = read_json(SETTINGS_FILE)
    code = data.get("lang")
    return {"lang": code if code in LANGUAGES else DEFAULT}


def current() -> str:
    return load()["lang"]


def is_english() -> bool:
    return current() == "en"


def save(code: str) -> dict:
    """Ganti bahasa; ValueError bila kodenya tidak dikenal."""
    if code not in LANGUAGES:
        raise ValueError(f"bahasa harus salah satu dari: {', '.join(LANGUAGES)}")
    with _lock:
        write_json(SETTINGS_FILE, {"lang": code, "updated_at": now_iso()})
    log.info("[bahasa] %s", LANGUAGES[code]["label"])
    return {"lang": code}


def pick(texts: dict, code: str | None = None):
    """Isi `texts` untuk bahasa yang aktif; jatuh ke bahasa bawaan bila belum diterjemahkan."""
    code = code or current()
    return texts.get(code, texts[DEFAULT])


def name(of: str, code: str | None = None) -> str:
    """Nama bahasa `of` dalam bahasa `code`, mis. name("en", "id") -> "bahasa Inggris"."""
    return pick(NAMES[of], code)


def tts_code(code: str | None = None) -> str:
    return LANGUAGES[code or current()]["tts"]


def stt_code(code: str | None = None) -> str:
    return LANGUAGES[code or current()]["stt"]


def label(code: str | None = None) -> str:
    return LANGUAGES[code or current()]["label"]


# --------------------------------- tool -----------------------------------
def set_language(language: str) -> dict:
    """Tool agent: ganti bahasa EduPad (semua suara, layar, dan jawaban)."""
    code = {"indonesia": "id", "indonesian": "id", "inggris": "en", "english": "en"}.get(
        language.strip().lower(), language.strip().lower()
    )
    try:
        data = save(code)
    except ValueError as e:
        return {"error": str(e)}
    return {
        "bahasa": label(data["lang"]),
        "petunjuk": "Konfirmasi singkat DALAM BAHASA BARU: mulai sekarang semua jawaban, "
        "pemberitahuan, dan layar memakai bahasa itu, dan sebutkan cara kembali "
        f'("{name(DEFAULT if data["lang"] != DEFAULT else "en", data["lang"])}").',
    }


TOOLS = {"set_language": set_language}

SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "set_language",
            "description": "Ganti bahasa EduPad (suara, layar, dan jawaban) ke bahasa Indonesia "
            "atau Inggris. Dipakai bila mahasiswa minta dijawab dalam bahasa lain.",
            "parameters": {
                "type": "object",
                "properties": {
                    "language": {"type": "string", "enum": list(LANGUAGES)},
                },
                "required": ["language"],
            },
        },
    }
]
