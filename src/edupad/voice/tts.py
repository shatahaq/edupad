"""Text-to-speech untuk jawaban EduPad.

Keluaran selalu PCM 16-bit mono 16 kHz (format yang langsung diputar ESP32-S3).
`stream()` mengirim audio per potongan begitu tersedia, sehingga perangkat bisa
mulai bicara sebelum seluruh kalimat selesai disintesis. Penyedia dipilih lewat
EDUPAD_TTS_PROVIDER di .env.

Beberapa akun ElevenLabs boleh diisi di .env (API_KEY_ElevenLabs, ...2, ...3 dengan
Voice_ID_ElevenLabs masing-masing). Akun dipakai berurutan: begitu satu akun menolak karena
kuotanya habis (atau key-nya ditolak), akun itu dilewati selama BLOCK_SECONDS dan permintaan
diulang ke akun berikutnya, tanpa menampilkan galat ke mahasiswa.

Waktu sampai audio pertama sebanding dengan panjang teks (uji: 123 karakter 0,97 s,
~330 karakter 2,2-2,5 s). Jawaban panjang karena itu dipecah: kalimat pertama dan sisanya
disintesis bersamaan, masing-masing diberi teks pasangannya sebagai konteks
(previous_text/next_text, tidak ditagih) agar intonasi tetap menyambung. Karakter yang
ditagih sama dengan satu permintaan utuh.
"""

from __future__ import annotations

import contextlib
import io
import logging
import queue
import re
import threading
import time
import wave
from collections.abc import Callable, Iterator

import requests

from edupad.config import get_settings
from edupad.core import http_pool
from edupad.voice import lang

log = logging.getLogger(__name__)

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
# Akun yang kuotanya habis dilewati selama ini; kuota gratis pulih bulanan, top-up kapan saja.
BLOCK_SECONDS = 6 * 3600
_blocked: dict[str, float] = {}  # API key -> time.monotonic() kapan boleh dicoba lagi
_blocked_lock = threading.Lock()


class TTSError(RuntimeError):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def accounts() -> list[tuple[str, str]]:
    """Akun ElevenLabs yang dicoba sekarang, urut seperti di .env. Akun yang kuotanya habis
    ditaruh paling belakang (bukan dibuang), jadi tetap ada yang dicoba walau semuanya pernah
    habis - kuota bisa saja sudah pulih atau diisi ulang."""
    configured = [(key, voice) for key, voice in get_settings().elevenlabs_accounts if voice]
    if not configured:
        raise TTSError("API_KEY_ElevenLabs / Voice_ID_ElevenLabs belum diisi di .env")
    now = time.monotonic()
    with _blocked_lock:
        ready = [a for a in configured if _blocked.get(a[0], 0.0) <= now]
        blocked = [a for a in configured if _blocked.get(a[0], 0.0) > now]
    return ready + blocked


def _block(api_key: str, message: str) -> None:
    with _blocked_lock:
        _blocked[api_key] = time.monotonic() + BLOCK_SECONDS
    log.warning(
        "[tts] akun ElevenLabs ...%s dilewati %d jam: %s",
        api_key[-4:],
        BLOCK_SECONDS // 3600,
        message,
    )


def _account_problem(error: TTSError) -> bool:
    """True bila yang bermasalah akunnya (kuota habis, key ditolak/dicabut), bukan permintaannya.
    Voice yang tidak ada (404) bukan di sini: itu salah isi .env dan harus kelihatan."""
    return error.status in (401, 402, 403) or "quota" in str(error).lower()


def _open(api_key: str, voice_id: str, payload: dict) -> requests.Response:
    """Mulai stream TTS satu akun; TTSError bila ditolak (status ikut terbawa)."""
    try:
        response = http_pool.post(
            ELEVENLABS_URL.format(voice_id=voice_id),
            params={"output_format": f"pcm_{SAMPLE_RATE}"},
            headers={"xi-api-key": api_key},
            json=payload,
            stream=True,
            timeout=TIMEOUT,
        )
    except requests.RequestException as e:
        raise TTSError(f"ElevenLabs tidak bisa dihubungi: {e}") from e
    if response.ok:
        return response
    with response:
        try:
            detail = response.json().get("detail", {})
            message = detail.get("message") if isinstance(detail, dict) else str(detail)
        except ValueError:
            message = response.text[:200]
    raise TTSError(f"ElevenLabs HTTP {response.status_code}: {message}", response.status_code)


def _elevenlabs(
    text: str,
    previous_text: str | None = None,
    next_text: str | None = None,
    speed: float | None = None,
) -> Iterator[bytes]:
    payload = {
        "text": text,
        "model_id": get_settings().tts_model,
        "language_code": lang.tts_code(),
        "voice_settings": {**VOICE_SETTINGS, **({"speed": speed} if speed else {})},
        "seed": SEED,
    }
    payload.update(
        {k: v for k, v in (("previous_text", previous_text), ("next_text", next_text)) if v}
    )
    available = accounts()
    for number, (api_key, voice_id) in enumerate(available, start=1):
        try:
            response = _open(api_key, voice_id, payload)
        except TTSError as e:
            if not _account_problem(e):
                raise  # permintaannya yang salah (mis. voice tidak ada), bukan akunnya
            _block(api_key, str(e))
            if number == len(available):
                raise  # tidak ada akun lain: galat akun terakhir yang dilaporkan
            continue
        if number > 1:
            log.info("[tts] memakai akun ElevenLabs ke-%d (...%s)", number, api_key[-4:])
        with response:
            try:
                yield from (chunk for chunk in response.iter_content(CHUNK_BYTES) if chunk)
            except requests.RequestException as e:
                raise TTSError(f"stream ElevenLabs terputus: {e}") from e
        return


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
