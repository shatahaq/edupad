"""Perkenalan diri EduPad, diputar perangkat setiap kali menyala.

Suaranya dibuat sekali lewat TTS lalu disimpan di data/voice/intro/ (intro.pcm + intro.json),
jadi menyalakan perangkat tidak memakai kuota TTS. Dibuat ulang hanya bila naskah atau
pengaturan suara berubah. Naskah dipecah per kalimat supaya perangkat tahu kapan tiap kalimat
mulai: teks di layar dan gerakan burung hantu ikut berganti. Tiap kalimat disintesis dengan
kalimat sebelum/sesudahnya sebagai konteks agar intonasinya tetap menyambung.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from array import array

from edupad.agent.formatting import to_display_text
from edupad.config import VOICE_DIR, get_settings
from edupad.voice import tts

log = logging.getLogger(__name__)

# (gerakan burung hantu di layar, kalimat). Gerakan dikenali firmware (display.cpp):
# wave, happy, book, tasks, button, cheer; selain itu burung hantu hanya bicara.
SCRIPT = [
    ("wave", "Halo! Aku EduPad."),
    ("happy", "Teman belajarmu."),
    ("book", "Aku bisa menjelaskan materi kuliahmu,"),
    ("tasks", "mengecek tugas, deadline, dan presensi."),
    ("button", "Caranya gampang: tahan tombol, lalu tanya saja."),
    ("cheer", "Yuk, mulai belajar!"),
]
GAP_SECONDS = 0.2  # jeda antarkalimat
EDGE_SECONDS = 0.06  # hening yang disisakan di awal/akhir tiap kalimat setelah dipangkas
SILENCE = 500  # amplitudo (dari 32767) yang dianggap hening, ~-36 dBFS
AUDIO_URL = "/v1/intro/audio"
INTRO_DIR = VOICE_DIR / "intro"
BYTES_PER_SECOND = tts.SAMPLE_RATE * tts.SAMPLE_WIDTH

_lock = threading.Lock()  # dua perangkat menyala bersamaan: TTS tetap hanya dipanggil sekali


def _version() -> str:
    """Berubah bila naskah atau suara berubah, sehingga simpanan lama dibuat ulang."""
    s = get_settings()
    raw = json.dumps(
        [SCRIPT, GAP_SECONDS, s.tts_provider, s.tts_model, s.elevenlabs_voice_id]
        + [tts.VOICE_SETTINGS, tts.SEED]
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def trim(pcm: bytes) -> bytes:
    """Buang hening di awal dan akhir (sisakan EDGE_SECONDS) supaya waktu tiap kalimat tepat."""
    samples = array("h", pcm[: len(pcm) - len(pcm) % tts.SAMPLE_WIDTH])
    loud = [i for i, v in enumerate(samples) if abs(v) > SILENCE]
    if not loud:
        return b""
    edge = int(EDGE_SECONDS * tts.SAMPLE_RATE)
    return samples[max(0, loud[0] - edge) : loud[-1] + 1 + edge].tobytes()


def _generate(version: str) -> tuple[dict, bytes]:
    texts = [text for _, text in SCRIPT]
    gap = b"\0" * (int(GAP_SECONDS * tts.SAMPLE_RATE) * tts.SAMPLE_WIDTH)
    parts: list[bytes] = []
    segments, size = [], 0
    for i, (gesture, text) in enumerate(SCRIPT):
        pcm = trim(
            tts.synthesize_part(
                text,
                previous_text=" ".join(texts[:i]) or None,
                next_text=" ".join(texts[i + 1 :]) or None,
            )
        )
        if parts:
            parts.append(gap)
            size += len(gap)
        segments.append(
            {
                "start": round(size / BYTES_PER_SECOND, 3),
                "gesture": gesture,
                "text": to_display_text(text),
            }
        )
        parts.append(pcm)
        size += len(pcm)
    pcm = b"".join(parts)
    meta = {
        "version": version,
        "duration": round(len(pcm) / BYTES_PER_SECOND, 3),
        "audio_url": AUDIO_URL,
        "segments": segments,
    }
    log.info(
        "[intro] suara perkenalan dibuat: %.1f detik, %d kalimat", meta["duration"], len(SCRIPT)
    )
    return meta, pcm


def load(regenerate: bool = False) -> tuple[dict, bytes]:
    """(info untuk perangkat, PCM 16 kHz). Dibuat lewat TTS hanya bila belum ada atau usang."""
    meta_path, pcm_path = INTRO_DIR / "intro.json", INTRO_DIR / "intro.pcm"
    with _lock:
        version = _version()
        if not regenerate:
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                if meta.get("version") == version:
                    return meta, pcm_path.read_bytes()
            except (OSError, ValueError):
                pass
        meta, pcm = _generate(version)
        INTRO_DIR.mkdir(parents=True, exist_ok=True)
        # audio dulu, info (berisi versi) terakhir: bila terhenti di tengah, dibuat ulang lagi
        for path, data in ((pcm_path, pcm), (meta_path, json.dumps(meta, indent=1).encode())):
            tmp = path.with_suffix(".tmp")
            tmp.write_bytes(data)
            tmp.replace(path)
        return meta, pcm
