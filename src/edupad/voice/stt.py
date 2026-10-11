"""Speech-to-text untuk pertanyaan suara EduPad.

Masukan dari mikrofon ESP32-S3 berupa PCM 16-bit mono 16 kHz (format yang sama dengan
keluaran TTS), atau file audio (wav, mp3, m4a, ogg, flac, webm). Whisper diberi nama &
singkatan mata kuliah sebagai prompt agar "PV" dan "MSBD" ditulis benar.

Whisper mengubah hening/derau menjadi "Terima kasih." dan Groq tidak mengisi
no_speech_prob, jadi PCM tanpa ucapan disaring di sini lewat energi suara sebelum dikirim
(sekaligus hemat kuota). Penyedia dipilih lewat EDUPAD_STT_PROVIDER di .env.
"""

from __future__ import annotations

import io
import math
import operator
import re
import sys
import wave
from array import array
from collections.abc import Callable

import requests

from edupad.config import CORPUS_DIR, get_settings
from edupad.core import http_pool
from edupad.core.files import read_json
from edupad.voice.tts import SAMPLE_RATE, SAMPLE_WIDTH, duration_seconds, to_wav

GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
TIMEOUT = 30
MAX_FILE_BYTES = 25 * 1024 * 1024  # batas unggah Groq tier gratis
MIN_SECONDS = 0.3  # lebih pendek = tombol tak sengaja; Groq tetap menagih minimal 10 detik
MAX_SECONDS = 120  # pertanyaan suara jauh lebih pendek; ini pengaman kuota
MAX_PROMPT_CHARS = 600  # prompt Whisper dibatasi 224 token
# Uji rekaman suara EduPad: ucapan median -20 dBFS, derau ringan -47..-41 dBFS.
# Kalibrasi ulang dengan mikrofon ESP32 bila ucapan pelan ikut terbuang.
SPEECH_DBFS = -35.0
MIN_SPEECH_SECONDS = 0.25
FRAME_SAMPLES = SAMPLE_RATE * 30 // 1000  # 30 ms
CATALOG_FILE = CORPUS_DIR / "catalog.json"


class STTError(RuntimeError):
    pass


def vocabulary_prompt() -> str:
    """Kosakata EduPad + nama & singkatan mata kuliah di KRS; memandu ejaan saja."""
    names, acronyms = [], []
    for course in read_json(CATALOG_FILE).get("mata_kuliah", []):
        name = course.get("matkul", "")
        if name and not name.lower().startswith("praktikum "):
            names.append(name)
        acronyms += [a.upper() for a in course.get("alias", []) if re.fullmatch(r"[a-z]{2,5}", a)]
    words = [
        "EduPad",
        "jadwal kuliah",
        "tugas",
        "deadline",
        "pertemuan",
        "presensi",
        *names,
        *dict.fromkeys(acronyms),
    ]
    return (", ".join(words) + ".")[:MAX_PROMPT_CHARS]


def has_speech(pcm: bytes) -> bool:
    """True bila cukup banyak potongan 30 ms yang lebih keras dari SPEECH_DBFS."""
    samples = array("h")
    samples.frombytes(pcm[: len(pcm) - len(pcm) % SAMPLE_WIDTH])
    if sys.byteorder == "big":
        samples.byteswap()
    threshold = (32768 * 10 ** (SPEECH_DBFS / 20)) ** 2 * FRAME_SAMPLES  # jumlah kuadrat per frame
    needed = math.ceil(MIN_SPEECH_SECONDS * SAMPLE_RATE / FRAME_SAMPLES)
    loud = 0
    for start in range(0, len(samples) - FRAME_SAMPLES + 1, FRAME_SAMPLES):
        frame = samples[start : start + FRAME_SAMPLES]
        loud += sum(map(operator.mul, frame, frame)) > threshold
        if loud >= needed:
            return True
    return False


def _groq(audio: bytes, filename: str) -> str:
    settings = get_settings()
    if not settings.groq_api_key:
        raise STTError("API_KEY_GROQ belum diisi di .env")
    try:
        response = http_pool.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            files={"file": (filename, audio)},
            data={
                "model": settings.stt_model,
                "language": "id",
                "prompt": vocabulary_prompt(),
                "response_format": "json",
            },
            timeout=TIMEOUT,
        )
    except requests.RequestException as e:
        raise STTError(f"Groq tidak bisa dihubungi: {e}") from e
    if not response.ok:
        try:
            error = response.json().get("error", {})
            message = error.get("message") if isinstance(error, dict) else str(error)
        except ValueError:
            message = response.text[:200]
        raise STTError(f"Groq HTTP {response.status_code}: {message}")
    try:
        return response.json().get("text", "")
    except ValueError as e:
        raise STTError(f"jawaban Groq bukan JSON: {response.text[:200]}") from e


PROVIDERS: dict[str, Callable[[bytes, str], str]] = {"groq": _groq}


def transcribe(audio: bytes, filename: str = "audio.wav") -> str:
    """Teks dari isi file audio; "" bila kosong. Ekstensi `filename` menentukan format."""
    if not audio:
        return ""
    if len(audio) > MAX_FILE_BYTES:
        raise STTError(
            f"audio {len(audio) / 1e6:.1f} MB melebihi batas {MAX_FILE_BYTES / 1e6:.0f} MB"
        )
    provider = get_settings().stt_provider
    if provider not in PROVIDERS:
        raise STTError(
            f"EDUPAD_STT_PROVIDER '{provider}' tidak dikenal; pilihan: {', '.join(PROVIDERS)}"
        )
    text = " ".join(PROVIDERS[provider](audio, filename).split())
    return text if re.search(r"\w", text) else ""  # "." / "..." dari derau


def _device_pcm(wav: bytes) -> bytes | None:
    """Frame PCM bila `wav` mono 16-bit 16 kHz (format mikrofon ESP32-S3), selain itu None."""
    try:
        with wave.open(io.BytesIO(wav)) as w:
            if (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (
                1,
                SAMPLE_WIDTH,
                SAMPLE_RATE,
            ):
                return w.readframes(w.getnframes())
    except (wave.Error, EOFError):
        pass
    return None


def transcribe_file(audio: bytes, filename: str = "audio.wav") -> str:
    """Seperti transcribe(); WAV berformat perangkat diproses sebagai PCM (termasuk saring hening)."""
    pcm = _device_pcm(audio) if filename.lower().endswith(".wav") else None
    return transcribe_pcm(pcm) if pcm is not None else transcribe(audio, filename)


def transcribe_pcm(pcm: bytes) -> str:
    """Teks dari PCM 16 kHz mono 16-bit (mikrofon ESP32-S3); "" bila tidak ada ucapan."""
    pcm = pcm[: len(pcm) - len(pcm) % SAMPLE_WIDTH]
    seconds = duration_seconds(pcm)
    if seconds > MAX_SECONDS:
        raise STTError(f"audio {seconds:.0f} detik melebihi batas {MAX_SECONDS} detik")
    if seconds < MIN_SECONDS or not has_speech(pcm):
        return ""
    return transcribe(to_wav(pcm))
