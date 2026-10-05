"""Text-to-speech untuk jawaban EduPad.

Keluaran selalu PCM 16-bit mono 16 kHz (format yang langsung diputar ESP32-S3).
`stream()` mengirim audio per potongan begitu tersedia, sehingga perangkat bisa
mulai bicara sebelum seluruh kalimat selesai disintesis. Penyedia dipilih lewat
EDUPAD_TTS_PROVIDER di .env.
"""

from __future__ import annotations

import io
import wave
from collections.abc import Callable, Iterator

import requests

from edupad.config import get_settings

SAMPLE_RATE = 16_000
SAMPLE_WIDTH = 2  # 16-bit
CHUNK_BYTES = 3_200  # 100 ms audio
MAX_TEXT_CHARS = 1_000  # jawaban suara agent dibatasi ~450 karakter; ini pengaman kuota
TIMEOUT = 60

ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
# Dipilih dengan uji dengar (varian A): cukup ekspresif, nada & tempo tetap konsisten berkat seed.
VOICE_SETTINGS = {"stability": 0.55, "similarity_boost": 0.75, "style": 0.35, "speed": 1.05,
                  "use_speaker_boost": True}
SEED = 2026


class TTSError(RuntimeError):
    pass


def _elevenlabs(text: str) -> Iterator[bytes]:
    settings = get_settings()
    if not (settings.elevenlabs_api_key and settings.elevenlabs_voice_id):
        raise TTSError("API_KEY_ElevenLabs / Voice_ID_ElevenLabs belum diisi di .env")
    try:
        response = requests.post(
            ELEVENLABS_URL.format(voice_id=settings.elevenlabs_voice_id),
            params={"output_format": f"pcm_{SAMPLE_RATE}"},
            headers={"xi-api-key": settings.elevenlabs_api_key},
            json={"text": text, "model_id": settings.tts_model, "language_code": "id",
                  "voice_settings": VOICE_SETTINGS, "seed": SEED},
            stream=True, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise TTSError(f"ElevenLabs tidak bisa dihubungi: {e}") from e
    with response:
        if not response.ok:
            try:
                detail = response.json().get("detail", {})
                message = detail.get("message") if isinstance(detail, dict) else str(detail)
            except ValueError:
                message = response.text[:200]
            raise TTSError(f"ElevenLabs HTTP {response.status_code}: {message}")
        yield from (chunk for chunk in response.iter_content(CHUNK_BYTES) if chunk)


PROVIDERS: dict[str, Callable[[str], Iterator[bytes]]] = {"elevenlabs": _elevenlabs}


def stream(text: str) -> Iterator[bytes]:
    """Potongan PCM 16 kHz mono 16-bit, berurutan."""
    text = " ".join(text.split())
    if not text:
        return iter(())
    if len(text) > MAX_TEXT_CHARS:
        raise TTSError(f"teks {len(text)} karakter melebihi batas {MAX_TEXT_CHARS}")
    provider = get_settings().tts_provider
    if provider not in PROVIDERS:
        raise TTSError(f"EDUPAD_TTS_PROVIDER '{provider}' tidak dikenal; pilihan: {', '.join(PROVIDERS)}")
    return PROVIDERS[provider](text)


def synthesize(text: str) -> bytes:
    return b"".join(stream(text))


def to_wav(pcm: bytes) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(SAMPLE_WIDTH)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm)
    return buffer.getvalue()


def duration_seconds(pcm: bytes) -> float:
    return len(pcm) / (SAMPLE_RATE * SAMPLE_WIDTH)
