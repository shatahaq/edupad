"""Pesan status bersuara untuk Mode Suara (voice/mode.py).

Firmware 1.2 mengunduh semua pesan ini ke PSRAM saat Mode Suara aktif, lalu memutarnya sendiri
untuk kejadian yang tidak punya jawaban dari server: Wi-Fi putus, server tidak terjangkau,
suara tidak terdengar, dan seterusnya. Karena itu pesannya tetap terdengar walau perangkat
sedang offline. Suaranya dibuat sekali lewat TTS dan disimpan di data/voice/clips/; dibuat ulang
hanya bila teks, suara, atau kecepatan bicara berubah (tidak memakai kuota TTS setiap kali).
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading

from edupad.config import VOICE_DIR, get_settings
from edupad.voice import intro, tts
from edupad.voice import mode as voice_mode

log = logging.getLogger(__name__)

CLIPS_DIR = VOICE_DIR / "clips"
URL_PREFIX = "/v1/voice/clip/"
# Nama dipakai firmware (firmware/edupad/voice.cpp); tambah di sana juga bila menambah di sini.
CLIPS = {
    "wifi": "Wi-Fi terputus. EduPad sedang mencoba menyambung lagi.",
    "send": "Pertanyaanmu gagal terkirim. Tahan tombol untuk mencoba lagi.",
    "server": "Server EduPad tidak bisa dihubungi. Coba lagi sebentar lagi.",
    "error": "Maaf, sedang ada gangguan. Coba tanyakan lagi sebentar lagi.",
    "no_speech": "Suaramu tidak terdengar. Tahan tombol, lalu bicara lagi.",
    "audio": "Suara jawaban gagal diputar. Tekan tombol sekali untuk mengulang.",
    "no_answer": "Belum ada jawaban untuk diulang. Tahan tombol, lalu bicara.",
    "new_session": "Percakapan baru dimulai.",
}

_lock = threading.Lock()  # dua permintaan bersamaan: TTS tetap hanya dipanggil sekali


def _version(name: str, speed: float) -> str:
    s = get_settings()
    raw = json.dumps(
        [CLIPS[name], s.tts_provider, s.tts_model, s.elevenlabs_voice_id, tts.VOICE_SETTINGS]
        + [tts.SEED, speed]
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def urls() -> dict[str, str]:
    """Alamat tiap pesan. `v` berganti bila suaranya berubah (mis. kecepatan bicara), sehingga
    perangkat tahu harus mengunduh ulang."""
    speed = voice_mode.speed_value()
    return {name: f"{URL_PREFIX}{name}?v={_version(name, speed)}" for name in CLIPS}


def load(name: str) -> bytes:
    """PCM 16 kHz pesan `name`; KeyError bila tidak dikenal, tts.TTSError bila TTS gagal."""
    text = CLIPS[name]
    speed = voice_mode.speed_value()
    path = CLIPS_DIR / f"{name}-{_version(name, speed)}.pcm"
    with _lock:
        try:
            return path.read_bytes()
        except OSError:
            pass
        pcm = intro.trim(tts.synthesize_part(text, speed=speed))
        CLIPS_DIR.mkdir(parents=True, exist_ok=True)
        for old in CLIPS_DIR.glob(f"{name}-*.pcm"):  # versi lama (teks/kecepatan berubah)
            old.unlink(missing_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(pcm)
        tmp.replace(path)
        log.info("[mode suara] pesan %s dibuat (%.1f s)", name, tts.duration_seconds(pcm))
        return pcm
