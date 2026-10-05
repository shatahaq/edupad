"""Path, URL, dan pengaturan dari file .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import timedelta, timezone
from pathlib import Path

BASE_DIR = Path(os.environ.get("EDUPAD_HOME") or Path(__file__).resolve().parents[2])

DATA_DIR = BASE_DIR / "data"
MATERIALS_DIR = DATA_DIR / "materials"
MARKDOWN_DIR = DATA_DIR / "markdown"
CORPUS_DIR = DATA_DIR / "corpus"
ASSIGNMENTS_DIR = DATA_DIR / "assignments"
SCHEDULE_DIR = DATA_DIR / "schedule"
VOICE_DIR = DATA_DIR / "voice"
LOG_DIR = BASE_DIR / "logs"

# Rahasia: cookie sesi & profil browser. Jangan dibagikan.
STATE_DIR = BASE_DIR / "user_data"
BROWSER_PROFILE_DIR = STATE_DIR
SATU_PROFILE_DIR = STATE_DIR / "satu_profile"
MOODLE_SESSION_FILE = STATE_DIR / "session.json"
SATU_SESSION_FILE = STATE_DIR / "satu_session.json"
STATE_FILE = STATE_DIR / "session_state.json"
SCRAPER_LOCK_FILE = STATE_DIR / "scraper.lock"
# Token portal SATU dirotasi saat diperbarui; dua proses yang memperbarui bersamaan
# membuat salah satunya gagal (RefreshAccessTokenError), jadi aksesnya bergiliran.
SATU_LOCK_FILE = STATE_DIR / "satu_session.lock"
ENV_FILE = BASE_DIR / ".env"

MOODLE_URL = "https://kelas.usu.ac.id"
SATU_URL = "https://satu.usu.ac.id/mahasiswa"

SUPABASE_URL = "https://ifirfvbgumjqqywfbuoj.supabase.co"  # project "AI-Agent"
DEEPSEEK_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-flash"  # DeepSeek-V4.1-Flash

WIB = timezone(timedelta(hours=7), "WIB")
REQUEST_DELAY = 2.5  # detik antar request halaman; jangan diturunkan
REQUEST_TIMEOUT = 30

# Koordinat Universitas Sumatera Utara (Kampus USU Padang Bulan)
USU_LATITUDE = 3.5651
USU_LONGITUDE = 98.6565
# display_name Nominatim untuk koordinat di atas; portal mengirim teks ini sebagai `location`
USU_LOCATION = "BNI, Jalan Sivitas Akademika, Padang Bulan, Medan Baru, Kota Medan, Sumatera Utara, 20155, Indonesia"


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str | None
    telegram_chat_id: str | None
    student_class: str | None
    ignored_courses: frozenset[str]
    user_id: str
    supabase_url: str
    supabase_key: str | None
    llm_api_key: str | None
    llm_model: str
    llm_effort: str
    cloudflare_account_id: str | None
    cloudflare_api_token: str | None
    tts_provider: str
    tts_model: str
    elevenlabs_api_key: str | None
    elevenlabs_voice_id: str | None


def load_env(path: Path = ENV_FILE) -> None:
    """Baca KEY=VALUE dari .env tanpa menimpa environment yang sudah ada."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def _env(*names: str) -> str | None:
    """Nilai env pertama yang terisi; nama lama tetap didukung."""
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return None


def get_settings() -> Settings:
    load_env()
    ignored = _env("EDUPAD_IGNORED_COURSES", "TUGAS_ABAIKAN_COURSE") or ""
    student_class = _env("EDUPAD_CLASS", "KELAS_SAYA")
    return Settings(
        telegram_bot_token=_env("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=_env("TELEGRAM_CHAT_ID"),
        student_class=student_class.upper() if student_class else None,
        ignored_courses=frozenset(x.strip() for x in ignored.split(",") if x.strip()),
        user_id=_env("EDUPAD_USER_ID") or "default",
        supabase_url=_env("SUPABASE_URL") or SUPABASE_URL,
        supabase_key=_env("SUPABASE_SECRET_KEY", "SUPABASE_SERVICE_ROLE_KEY"),
        llm_api_key=_env("API_KEY_AI", "DEEPSEEK_API_KEY"),
        llm_model=_env("EDUPAD_LLM_MODEL") or DEEPSEEK_MODEL,
        llm_effort=_env("EDUPAD_LLM_EFFORT") or "low",  # low/high/max; low = respons suara lebih cepat
        cloudflare_account_id=_env("CLOUDFLARE_ACCOUNT_ID"),
        cloudflare_api_token=_env("CLOUDFLARE_API_TOKEN"),
        tts_provider=(_env("EDUPAD_TTS_PROVIDER") or "elevenlabs").lower(),
        tts_model=_env("EDUPAD_TTS_MODEL") or "eleven_multilingual_v2",
        elevenlabs_api_key=_env("ELEVENLABS_API_KEY", "API_KEY_ElevenLabs"),
        elevenlabs_voice_id=_env("ELEVENLABS_VOICE_ID", "Voice_ID_ElevenLabs"),
    )
