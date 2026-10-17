"""Text-to-speech untuk jawaban EduPad.

Keluaran selalu PCM 16-bit mono 16 kHz (format yang langsung diputar ESP32-S3).
`stream()` mengirim audio per potongan begitu tersedia, sehingga perangkat bisa
mulai bicara sebelum seluruh kalimat selesai disintesis. Penyedia dipilih lewat
EDUPAD_TTS_PROVIDER di .env.

Waktu sampai audio pertama sebanding dengan panjang teks (uji: 123 karakter 0,97 s,
~330 karakter 2,2-2,5 s). Jawaban panjang karena itu dipecah: kalimat pertama dan sisanya
disintesis bersamaan, masing-masing diberi teks pasangannya sebagai konteks
(previous_text/next_text, tidak ditagih) agar intonasi tetap menyambung. Karakter yang
ditagih sama dengan satu permintaan utuh.
"""

from __future__ import annotations

import contextlib
import io
import queue
import re
import threading
import wave
from collections.abc import Callable, Iterator

import requests

from edupad.config import get_settings
from edupad.core import http_pool

SAMPLE_RATE = 16_000
SAMPLE_WIDTH = 2  # 16-bit
CHUNK_BYTES = 3_200  # 100 ms audio
MAX_TEXT_CHARS = 1_000  # jawaban suara agent dibatasi ~450 karakter; ini pengaman kuota
TIMEOUT = 60

ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
# Dipilih dengan uji dengar (varian A): cukup ekspresif, nada & tempo tetap konsisten berkat seed.
VOICE_SETTINGS = {
    "stability": 0.55,
    "similarity_boost": 0.75,
    "style": 0.35,
    "speed": 1.05,
    "use_speaker_boost": True,
}
SEED = 2026
# Dipecah bila teks >= SPLIT_MIN_TOTAL dan kalimat pertamanya SPLIT_MIN_FIRST..SPLIT_MAX_FIRST
# karakter: bagian pertama >= ~4 detik suara, cukup untuk menutupi waktu sisanya disiapkan.
SPLIT_MIN_TOTAL = 120
SPLIT_MIN_FIRST = 60
SPLIT_MAX_FIRST = 200
MAX_CONCURRENT = 2  # batas permintaan paralel ElevenLabs akun gratis (model selain Flash/Turbo)
_SLOTS = threading.BoundedSemaphore(MAX_CONCURRENT)


class TTSError(RuntimeError):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def _elevenlabs(
    text: str,
    previous_text: str | None = None,
    next_text: str | None = None,
    speed: float | None = None,
) -> Iterator[bytes]:
    settings = get_settings()
    if not (settings.elevenlabs_api_key and settings.elevenlabs_voice_id):
        raise TTSError("API_KEY_ElevenLabs / Voice_ID_ElevenLabs belum diisi di .env")
    payload = {
        "text": text,
        "model_id": settings.tts_model,
        "language_code": "id",
        "voice_settings": {**VOICE_SETTINGS, **({"speed": speed} if speed else {})},
        "seed": SEED,
    }
    payload.update(
        {k: v for k, v in (("previous_text", previous_text), ("next_text", next_text)) if v}
    )
    try:
        response = http_pool.post(
            ELEVENLABS_URL.format(voice_id=settings.elevenlabs_voice_id),
            params={"output_format": f"pcm_{SAMPLE_RATE}"},
            headers={"xi-api-key": settings.elevenlabs_api_key},
            json=payload,
            stream=True,
            timeout=TIMEOUT,
        )
    except requests.RequestException as e:
        raise TTSError(f"ElevenLabs tidak bisa dihubungi: {e}") from e
    with response:
        if not response.ok:
            try:
                detail = response.json().get("detail", {})
                message = detail.get("message") if isinstance(detail, dict) else str(detail)
            except ValueError:
                message = response.text[:200]
            raise TTSError(
                f"ElevenLabs HTTP {response.status_code}: {message}", response.status_code
            )
        try:
            yield from (chunk for chunk in response.iter_content(CHUNK_BYTES) if chunk)
        except requests.RequestException as e:
            raise TTSError(f"stream ElevenLabs terputus: {e}") from e


PROVIDERS: dict[str, Callable[..., Iterator[bytes]]] = {"elevenlabs": _elevenlabs}


def split_first(text: str) -> list[str]:
    """[kalimat pertama, sisanya], atau [text] bila memecah tidak mempercepat audio pertama."""
    if len(text) < SPLIT_MIN_TOTAL:
        return [text]
    for end in (m.end() for m in re.finditer(r"[.!?](?=\s)", text)):
        if end > SPLIT_MAX_FIRST:
            break
        if end >= SPLIT_MIN_FIRST:
            return [text[:end], text[end:].strip()]
    return [text]


class _Download:
    """Satu permintaan TTS, diunduh secepatnya di thread sendiri ke antrean.

    Slot ElevenLabs langsung lepas walau perangkat membaca audio pelan (sambil memutar), dan
    bagian berikutnya sudah siap saat bagian sebelumnya habis diputar.
    """

    def __init__(
        self,
        provider: Callable[..., Iterator[bytes]],
        text: str,
        retry_after: threading.Event | None = None,
        **context: str | float,
    ):
        self.done = threading.Event()
        self._provider, self._text, self._context = provider, text, context
        self._retry_after = retry_after
        self._queue: queue.Queue[bytes | BaseException | None] = queue.Queue()
        self._cancelled = threading.Event()
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        try:
            try:
                self._fetch()
            except TTSError as e:
                if e.status != 429 or self._retry_after is None:
                    raise
                # Slot dipakai di tempat lain: ulangi sekali setelah bagian sebelumnya selesai.
                self._retry_after.wait(TIMEOUT)
                self._fetch()
            self._queue.put(None)
        except BaseException as e:  # noqa: BLE001 - diteruskan ke thread yang memutar audio
            self._queue.put(e)
        finally:
            self.done.set()

    def _fetch(self) -> None:
        with _SLOTS, contextlib.closing(self._provider(self._text, **self._context)) as chunks:
            if self._cancelled.is_set():
                return  # dibatalkan selagi menunggu slot: jangan memakai kuota
            for chunk in chunks:
                if self._cancelled.is_set():
                    return
                self._queue.put(chunk)

    def __iter__(self) -> Iterator[bytes]:
        while (item := self._queue.get()) is not None:
            if isinstance(item, BaseException):
                raise item
            yield item

    def cancel(self) -> None:
        self._cancelled.set()


def _play(*downloads: _Download) -> Iterator[bytes]:
    try:
        for download in downloads:
            yield from download
    finally:
        for download in downloads:  # pendengar berhenti di tengah: hentikan unduhan
            download.cancel()


def _provider() -> Callable[..., Iterator[bytes]]:
    name = get_settings().tts_provider
    if name not in PROVIDERS:
        raise TTSError(
            f"EDUPAD_TTS_PROVIDER '{name}' tidak dikenal; pilihan: {', '.join(PROVIDERS)}"
        )
    return PROVIDERS[name]


def stream(text: str, speed: float | None = None) -> Iterator[bytes]:
    """Potongan PCM 16 kHz mono 16-bit, berurutan. `speed` menggantikan kecepatan bawaan."""
    text = " ".join(text.split())
    if not text:
        return iter(())
    if len(text) > MAX_TEXT_CHARS:
        raise TTSError(f"teks {len(text)} karakter melebihi batas {MAX_TEXT_CHARS}")
    provider = _provider()
    extra = {"speed": speed} if speed else {}
    parts = split_first(text)
    if len(parts) == 1:
        return _play(_Download(provider, text, **extra))
    first, rest = parts
    head = _Download(provider, first, next_text=rest, **extra)
    return _play(
        head, _Download(provider, rest, retry_after=head.done, previous_text=first, **extra)
    )


def synthesize_part(
    text: str,
    previous_text: str | None = None,
    next_text: str | None = None,
    speed: float | None = None,
) -> bytes:
    """Satu bagian dari naskah yang lebih panjang. Teks sebelum/sesudahnya hanya konteks
    intonasi (tidak ikut disuarakan dan tidak ditagih)."""
    text = " ".join(text.split())
    if not text:
        return b""
    if len(text) > MAX_TEXT_CHARS:
        raise TTSError(f"teks {len(text)} karakter melebihi batas {MAX_TEXT_CHARS}")
    extra = {"speed": speed} if speed else {}
    with _SLOTS:
        return b"".join(
            _provider()(text, previous_text=previous_text, next_text=next_text, **extra)
        )


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
