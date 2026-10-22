"""Pesan status bersuara untuk Mode Suara (voice/mode.py).

Firmware 1.2 mengunduh semua pesan ini ke PSRAM saat Mode Suara aktif, lalu memutarnya sendiri
untuk kejadian yang tidak punya jawaban dari server: Wi-Fi putus, server tidak terjangkau,
suara tidak terdengar, dan seterusnya. Karena itu pesannya tetap terdengar walau perangkat
sedang offline. Suaranya dibuat sekali lewat TTS dan disimpan di data/voice/clips/; dibuat ulang
hanya bila teks, suara, atau kecepatan bicara berubah (tidak memakai kuota TTS setiap kali).

Tiap pesan punya versi bahasa Indonesia dan Inggris (voice/lang.py); yang dipakai mengikuti
setelan bahasa, dan suara bahasa lain yang sudah dibuat tetap disimpan.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from collections.abc import Iterable

from edupad.config import VOICE_DIR, get_settings
from edupad.voice import intro, lang, tts
from edupad.voice import mode as voice_mode

log = logging.getLogger(__name__)

CLIPS_DIR = VOICE_DIR / "clips"
URL_PREFIX = "/v1/voice/clip/"
# Nama dipakai firmware (firmware/edupad/voice.cpp); tambah di sana juga bila menambah di sini.
CLIPS = {
    "ready": {
        "id": "EduPad siap. Tahan tombol, lalu tanya saja.",
        "en": "EduPad is ready. Hold the button, then just ask.",
    },
    "wifi": {
        "id": "Wi-Fi terputus. EduPad sedang mencoba menyambung lagi.",
        "en": "Wi-Fi is disconnected. EduPad is trying to reconnect.",
    },
    "send": {
        "id": "Pertanyaanmu gagal terkirim. Tahan tombol untuk mencoba lagi.",
        "en": "Your question could not be sent. Hold the button to try again.",
    },
    "server": {
        "id": "Server EduPad tidak bisa dihubungi. Coba lagi sebentar lagi.",
        "en": "The EduPad server cannot be reached. Please try again in a moment.",
    },
    "error": {
        "id": "Maaf, sedang ada gangguan. Coba tanyakan lagi sebentar lagi.",
        "en": "Sorry, something went wrong. Please ask again in a moment.",
    },
    "no_speech": {
        "id": "Suaramu tidak terdengar. Tahan tombol, lalu bicara lagi.",
        "en": "I could not hear you. Hold the button, then speak again.",
    },
    "audio": {
        "id": "Suara jawaban gagal diputar. Tekan tombol sekali untuk mengulang.",
        "en": "The answer could not be played. Press the button once to replay it.",
    },
    "no_answer": {
        "id": "Belum ada jawaban untuk diulang. Tahan tombol, lalu bicara.",
        "en": "There is no answer to replay yet. Hold the button, then speak.",
    },
    "new_session": {
        "id": "Percakapan baru dimulai.",
        "en": "Starting a new conversation.",
    },
}

_lock = threading.Lock()  # dua permintaan bersamaan: TTS tetap hanya dipanggil sekali


def version(text: str, speed: float) -> str:
    """Penanda versi suara satu kalimat; berganti bila teks, suara, atau kecepatannya berubah."""
    s = get_settings()
    raw = json.dumps(
        [text, s.tts_provider, s.tts_model, s.elevenlabs_voice_id, tts.VOICE_SETTINGS]
        + [tts.SEED, speed]
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def text(name: str) -> str:
    """Kalimat pesan `name` dalam bahasa yang aktif."""
    return lang.pick(CLIPS[name])


def urls() -> dict[str, str]:
    """Alamat tiap pesan. `v` berganti bila suaranya berubah (bahasa atau kecepatan bicara),
    sehingga perangkat tahu harus mengunduh ulang."""
    speed = voice_mode.speed_value()
    return {name: f"{URL_PREFIX}{name}?v={version(text(name), speed)}" for name in CLIPS}


def load(name: str) -> bytes:
    """PCM 16 kHz pesan `name`; KeyError bila tidak dikenal, tts.TTSError bila TTS gagal."""
    return cached_pcm(name, text(name), voice_mode.speed_value(), CLIPS[name].values())


def cached_pcm(name: str, text: str, speed: float, variants: Iterable[str] = ()) -> bytes:
    """PCM 16 kHz untuk `text`, dibuat sekali lalu dibaca dari simpanan pada pemakaian berikutnya.
    `name` hanya nama berkasnya, jadi kalimat tetap lain (voice/commands.py) ikut memakai ini.
    `variants` semua terjemahan kalimat ini: suaranya ikut disimpan, tidak dibuang saat berganti
    bahasa."""
    path = CLIPS_DIR / f"{name}-{version(text, speed)}.pcm"
    with _lock:
        try:
            return path.read_bytes()
        except OSError:
            pass
        pcm = intro.trim(tts.synthesize_part(text, speed=speed))
        CLIPS_DIR.mkdir(parents=True, exist_ok=True)
        # Tiap bahasa (`variants`) dan kecepatan untuk teks ini disimpan sendiri, jadi berpindah
        # bahasa/kecepatan lalu kembali tidak memanggil TTS lagi. Yang dibuang hanya sisa dari
        # teks atau suara versi lama.
        keep = {version(t, s) for t in (variants or [text]) for s in voice_mode.SPEEDS.values()}
        for old in CLIPS_DIR.glob(f"{name}-*.pcm"):
            if old.stem.rsplit("-", 1)[-1] not in keep:
                old.unlink(missing_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(pcm)
        tmp.replace(path)
        log.info("[mode suara] pesan %s dibuat (%.1f s)", name, tts.duration_seconds(pcm))
        return pcm
