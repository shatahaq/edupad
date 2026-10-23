"""HTTP API untuk perangkat EduPad (ESP32-S3).

Satu pertanyaan = dua permintaan:

1. POST /v1/ask
   Badan: rekaman PCM 16-bit mono 16 kHz little-endian (application/octet-stream), WAV
   (audio/wav), atau JSON {"text": "..."} untuk uji tanpa mikrofon. Boleh dikirim sambil
   merekam (Transfer-Encoding: chunked). `?new=1` memulai sesi percakapan baru.
   Jawaban JSON selalu berisi `status` ("ok" / "no_speech" / "error") dan `screen` (LCD),
   jadi perangkat cukup menampilkan `screen`, lalu memutar `audio_url` bila tidak null.
2. GET <audio_url>
   Suara jawaban, PCM 16-bit mono 16 kHz (format sama dengan rekaman), dialirkan begitu
   ElevenLabs mengirimnya. Untuk perangkat (header X-Firmware) TTS sudah dimulai saat /v1/ask
   menjawab, tidak menunggu permintaan ini, sehingga suaranya sudah berjalan selagi layar
   tampil. Hanya suara jawaban terakhir yang disimpan (jawaban baru menimpanya dan
   membatalkan sintesis lama); putar ulang lewat URL yang sama atau GET /v1/audio/latest
   diambil dari simpanan tanpa memakai kuota TTS. `?format=adpcm` (firmware 1.7+) mengirim
   IMA ADPCM, seperempat ukuran PCM (voice/adpcm.py); `?format=wav` untuk didengar di laptop.
   Berlaku juga untuk /v1/intro/audio, /v1/speech, dan /v1/voice.

Perkenalan diri saat perangkat menyala: GET /v1/intro (kalimat, gerakan, waktu mulai) lalu
GET /v1/intro/audio. Suaranya dibuat sekali lalu disimpan (voice/intro.py).

GET /v1/updates (dicek perangkat berkala): kuliah berikutnya dan pemberitahuan presensi /
deadline untuk layar (agent/updates.py).

Mode Suara (voice/mode.py): /v1/updates dan /v1/ask memberi `voice_mode`; saat aktif tiap
pemberitahuan punya `audio_url` (GET /v1/speech/<kunci>) dan perangkat mengunduh pesan status
dari GET /v1/voice/clip/<nama> (voice/clips.py). Pemberitahuan presensi dibuka dan deadline
tugas membawa `audio_url` walau Mode Suara mati, jadi selalu terdengar.

Bahasa (voice/lang.py): /v1/updates dan /v1/ask memberi `language` ("id"/"en"); satu setelan itu
mengubah pengenalan suara, suara TTS, jawaban agent, dan semua kalimat tetap.

Perintah setelan ("aktifkan mode suara", "bicara lebih cepat") dijawab /v1/ask tanpa memanggil
agent: kalimatnya tetap dan suaranya tersimpan di disk, dilayani GET /v1/voice/reply/<nama>
(voice/commands.py), jadi tidak ada token LLM maupun kuota TTS yang terpakai.

Semua permintaan selain GET /v1/health wajib membawa header
`Authorization: Bearer <EDUPAD_DEVICE_TOKEN>`.

Path di luar /v1/ dilayani web EduPad (login Google, /api, halaman React): lihat webapp.py.
"""

from __future__ import annotations

import functools
import hashlib
import hmac
import itertools
import json
import logging
import secrets
import signal
import threading
import time
from collections import OrderedDict
from collections.abc import Callable, Iterator
from concurrent.futures import Future, ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from edupad import device_status
from edupad.agent import updates
from edupad.agent.formatting import clean_speech, fit_screen
from edupad.config import DEEPSEEK_URL, WEB_DIST_DIR, Settings, get_settings
from edupad.core import http_pool
from edupad.voice import adpcm, clips, commands, intro, lang, stt, tts
from edupad.voice import mode as voice_mode
from edupad.webapp import WebApp

log = logging.getLogger(__name__)

MAX_BODY_BYTES = 5 * 1024 * 1024  # rekaman 120 detik = 3,8 MB
READ_TIMEOUT = 30  # detik tanpa data dari perangkat sebelum koneksi diputus
AUDIO_FORMAT = f"pcm_s16le;rate={tts.SAMPLE_RATE};channels=1"
AUDIO_FORMATS = ("pcm", "adpcm", "wav")  # ?format=; selain itu PCM
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
WAV_TYPES = {"audio/wav", "audio/x-wav", "audio/wave"}
WARM_URLS = tuple(
    f"{u.scheme}://{u.netloc}"
    for u in map(urlsplit, (stt.GROQ_URL, DEEPSEEK_URL, tts.ELEVENLABS_URL))
)

NO_SPEECH_SCREEN = fit_screen(
    "EduPad", ["Suara tidak terdengar.", "Tekan tombol, lalu bicara lagi."]
)
ERROR_SCREEN = fit_screen("EduPad", ["Maaf, sedang ada gangguan.", "Coba lagi sebentar lagi."])


class RequestError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


class Agent:
    """Agent EduPad dengan memory Supabase, diatur agar perangkat menunggu sesingkat mungkin.

    - prepare(): saat perangkat mulai mengirim rekaman, memory dimuat dan koneksi ke Groq,
      DeepSeek, dan ElevenLabs dibuka, sehingga keduanya selesai selagi pengguna bicara / STT.
    - answer(): giliran disimpan ke memory (termasuk ringkasan otomatis) setelah jawaban dikirim.
    Semua akses memory lewat satu worker sehingga berurutan: memory pertanyaan berikutnya baru
    dimuat setelah giliran sebelumnya tersimpan. Jumlah panggilan LLM tidak berubah.
    """

    def __init__(self):
        self._worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="memory")

    def prepare(self, new_session: bool) -> Future:
        http_pool.warm(*WARM_URLS)
        return self._worker.submit(_load_memory, new_session)

    def answer(self, question: str, prepared: Future) -> dict:
        from edupad.agent.assistant import ask

        return ask(question, memory=prepared.result(), defer_save=self._save_later)

    def close(self) -> None:
        self._worker.shutdown(wait=True)  # giliran yang belum tersimpan diselesaikan dulu

    def _save_later(self, job: Callable[[], None]) -> None:
        self._worker.submit(_logged, job)


def _load_memory(new_session: bool):
    from edupad.agent import tutor
    from edupad.agent.assistant import open_memory

    try:
        memory = open_memory(new_session=new_session)
        if memory:
            memory.prefetch()
    except Exception as e:  # noqa: BLE001 - tanpa memory, agent tetap bisa menjawab
        log.warning("[!] memory tidak bisa dimuat, menjawab tanpa memory: %s", e)
        return None
    try:
        tutor.prefetch(getattr(memory, "user_id", None))  # kuis aktif, dipakai ask()
    except Exception as e:  # noqa: BLE001 - tanpa status kuis, agent tetap bisa menjawab
        log.warning("[!] status kuis tidak bisa dimuat: %s", e)
    return memory


def _logged(job: Callable[[], None]) -> None:
    try:
        job()
    except Exception:  # noqa: BLE001 - worker latar belakang tidak boleh diam-diam gagal
        log.exception("[x] giliran gagal disimpan ke memory")


class Synthesis:
    """Suara satu jawaban: PCM dari TTS dikumpulkan di thread sendiri dan dibaca setiap
    permintaan audio sambil sintesis masih berjalan.

    Dimulai saat jawaban selesai untuk perangkat (lihat Handler._ask), atau saat audionya
    pertama kali diminta. Berjalan terus walau perangkat berhenti di tengah, jadi putar ulang
    tidak memakai kuota TTS lagi; gagal di tengah tidak disimpan dan dicoba lagi saat diminta.
    """

    def __init__(self, audio_id: str, text: str):
        self.id, self.text = audio_id, text
        self._chunks: list[bytes] = []  # PCM sampel utuh, berurutan
        self._pcm: bytes | None = None  # gabungan _chunks setelah selesai
        self._error: Exception | None = None
        self._running = False
        self._cancelled = False
        self._cond = threading.Condition()

    @property
    def pcm(self) -> bytes | None:
        with self._cond:
            return self._pcm

    def start(self) -> None:
        """Mulai menyuarakan (sekali); setelah gagal, panggilan berikutnya mencoba lagi."""
        with self._cond:
            if self._running or self._pcm is not None or self._cancelled:
                return
            self._chunks, self._error, self._running = [], None, True
        threading.Thread(target=self._run, name=f"tts-{self.id}", daemon=True).start()

    def cancel(self) -> None:
        """Jawaban sudah diganti: hentikan sintesis supaya slot ElevenLabs (tts.MAX_CONCURRENT)
        bebas untuk jawaban baru."""
        with self._cond:
            self._cancelled = True
            self._cond.notify_all()

    def _run(self) -> None:
        started, first_at, carry, chunks = time.monotonic(), None, b"", iter(())
        try:
            chunks = tts.stream(self.text, speed=voice_mode.speed_value())
            for chunk in chunks:
                data = carry + chunk
                cut = len(data) - len(data) % tts.SAMPLE_WIDTH  # jangan memotong satu sampel
                data, carry = data[:cut], data[cut:]
                with self._cond:
                    if self._cancelled:
                        return
                    if data:
                        first_at = first_at or time.monotonic()
                        self._chunks.append(data)
                        self._cond.notify_all()
        except Exception as e:  # noqa: BLE001 - diteruskan ke permintaan yang sedang membaca
            log.warning("[!] TTS jawaban gagal: %s", e)
            with self._cond:
                self._error, self._running = e, False
                self._cond.notify_all()
            return
        finally:
            getattr(chunks, "close", lambda: None)()  # tutup koneksi ElevenLabs bila berhenti
        with self._cond:
            self._pcm, self._running = b"".join(self._chunks), False
            self._cond.notify_all()
            seconds = tts.duration_seconds(self._pcm)
        now = time.monotonic()
        log.info(
            "[tts] %d karakter -> %.1f dtk suara; audio pertama %.1f dtk, selesai %.1f dtk",
            len(self.text),
            seconds,
            (first_at or now) - started,
            now - started,
        )

    def read(self) -> Iterator[bytes]:
        """PCM per potongan dari awal, menunggu potongan berikutnya sampai selesai.
        Melempar error TTS (sebelum atau di tengah audio) ke pembaca."""
        index = 0
        while True:
            with self._cond:
                while (
                    index >= len(self._chunks)
                    and self._pcm is None
                    and self._error is None
                    and not self._cancelled
                ):
                    if not self._cond.wait(tts.TIMEOUT):
                        raise tts.TTSError(f"TTS tidak mengirim audio selama {tts.TIMEOUT} detik")
                if index < len(self._chunks):
                    chunk = self._chunks[index]
                    index += 1
                elif self._error is not None:
                    raise self._error
                elif self._cancelled:
                    raise tts.TTSError("suara diganti jawaban baru")
                else:
                    return
            yield chunk


class AudioStore:
    """Suara jawaban terakhir. Jawaban baru menimpa yang lama dan membatalkan sintesisnya.

    Putar ulang memakai PCM yang tersimpan sehingga kuota TTS hanya terpakai sekali per jawaban.
    Dua permintaan untuk jawaban yang belum disuarakan membaca satu sintesis yang sama.
    """

    LATEST = "latest"

    def __init__(self):
        self._latest: Synthesis | None = None
        self._lock = threading.Lock()

    def add(self, text: str) -> Synthesis:
        item = Synthesis(secrets.token_urlsafe(9), text)
        with self._lock:
            previous, self._latest = self._latest, item
        if previous:
            previous.cancel()
        return item

    def get(self, audio_id: str) -> Synthesis | None:
        with self._lock:
            item = self._latest
        if item and audio_id in (item.id, self.LATEST):
            return item
        return None


@functools.lru_cache(maxsize=8)
def _adpcm(pcm: bytes) -> bytes:
    """ADPCM dari PCM tersimpan (intro, pesan suara, putar ulang): di-encode sekali saja."""
    return adpcm.encode(pcm)


def _audio_format(query: dict) -> str:
    fmt = (query.get("format") or ["pcm"])[0]
    return fmt if fmt in AUDIO_FORMATS else "pcm"


class SpeechStore:
    """Pemberitahuan yang dibacakan Mode Suara: teks, lalu PCM-nya setelah pertama disuarakan.

    Kunci = hash teks + kecepatan, jadi pemberitahuan yang sama (pengecekan berikutnya, perangkat
    lain) tidak memakai kuota TTS lagi. Hanya MAX_ENTRIES terbaru yang disimpan.
    """

    MAX_ENTRIES = 32

    def __init__(self):
        self._items: OrderedDict[str, dict] = OrderedDict()
        self._lock = threading.Lock()

    def add(self, text: str, speed: float) -> str:
        key = hashlib.sha256(f"{speed}|{text}".encode()).hexdigest()[:16]
        with self._lock:
            item = self._items.pop(key, None) or {
                "text": text,
                "speed": speed,
                "pcm": None,
                "lock": threading.Lock(),
            }
            self._items[key] = item
            while len(self._items) > self.MAX_ENTRIES:
                self._items.popitem(last=False)
        return key

    def get(self, key: str) -> dict | None:
        with self._lock:
            return self._items.get(key)


class EduPadServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        address: tuple[str, int],
        token: str | None,
        agent: Agent | None = None,
        web: WebApp | None = None,
    ):
        super().__init__(address, Handler)
        self.token, self.agent, self.audio = token, agent or Agent(), AudioStore()
        self.speech = SpeechStore()
        self.web = web or WebApp()

    def server_close(self) -> None:
        super().server_close()
        self.agent.close()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"  # keep-alive: audio diambil lewat koneksi yang sama
    server_version = "EduPad/1"
    timeout = READ_TIMEOUT
    server: EduPadServer
    _streaming = False  # header audio sudah terkirim; error tidak boleh lagi ditulis sebagai JSON
    _head = False  # permintaan HEAD: header dikirim, badan dibuang

    def do_GET(self) -> None:
        self._handle(self._get)

    def do_POST(self) -> None:
        self._handle(self._post)

    def do_HEAD(self) -> None:
        """HEAD (pemantau uptime, pratinjau tautan) hanya untuk halaman/file statis dan
        /v1/health. Rute login dan audio menolak HEAD: menjalankannya akan menghabiskan
        state login sekali pakai atau kuota TTS."""
        path = urlsplit(self.path).path
        allowed = path == "/v1/health" or not path.startswith(("/v1/", "/api/", "/auth/"))
        wfile = self.wfile
        self._head = True
        try:
            if allowed:
                self._handle(self._get)
            else:
                self.send_response(405)
                self.send_header(
                    "Allow", "GET" if path.startswith(("/v1/", "/api/")) else "GET, POST"
                )
                self.send_header("Content-Length", "0")
                self.end_headers()
        finally:
            self._head = False
            self.wfile = wfile  # koneksi keep-alive dipakai lagi untuk permintaan berikutnya

    def end_headers(self) -> None:
        super().end_headers()
        if self._head:
            self.wfile = _DiscardBody()

    def log_message(self, format: str, *args) -> None:
        message = format % args
        if "/auth/google/callback?" in message:  # jangan simpan kode otorisasi Google di log
            message = message.replace(self.path, urlsplit(self.path).path)
        log.info("%s %s", self.address_string(), message)

    def _handle(self, route: Callable[[str, dict], None]) -> None:
        url = urlsplit(self.path)
        self._streaming = False
        try:
            route(url.path, parse_qs(url.query))
        except (BrokenPipeError, ConnectionResetError, TimeoutError) as e:
            log.warning("[!] koneksi perangkat terputus: %s", e)
            self.close_connection = True
        except Exception as e:  # noqa: BLE001 - perangkat harus tetap menerima layar error
            if self._streaming:
                log.exception("[x] audio %s terputus", url.path)
                self.close_connection = True
            elif isinstance(e, RequestError):
                log.warning("[!] %s %s -> %d %s", self.command, url.path, e.status, e)
                self._json(e.status, {"status": "error", "error": str(e), "screen": ERROR_SCREEN})
            else:
                log.exception("[x] %s %s gagal", self.command, url.path)
                self._json(
                    500,
                    {
                        "status": "error",
                        "error": f"{type(e).__name__}: {e}",
                        "screen": ERROR_SCREEN,
                    },
                )

    def _get(self, path: str, query: dict) -> None:
        if not path.startswith("/v1/"):
            self.server.web.handle(self, "GET", path, query)
            return
        if path == "/v1/health":
            self._json(200, {"status": "ok"})
            return
        self._authorize()
        if path.startswith("/v1/audio/"):
            self._audio(path.removeprefix("/v1/audio/"), _audio_format(query))
            return
        if path == "/v1/intro":
            self._json(200, self._intro()[0])
            return
        if path == "/v1/updates":
            # Kartu peringatan/pengulangan hanya untuk firmware yang mengenalnya (kirim X-Firmware).
            known = bool(self.headers.get("X-Firmware"))
            data = updates.updates(extra_cards=True) if known else updates.updates()
            self._json(200, self._with_voice(data))
            return
        if path.startswith("/v1/speech/"):
            self._speech(path.removeprefix("/v1/speech/"), _audio_format(query))
            return
        if path.startswith(clips.URL_PREFIX):
            name = path.removeprefix(clips.URL_PREFIX)
            if name not in clips.CLIPS:
                raise RequestError(404, f"tidak ada pesan suara {name}")
            try:
                pcm = clips.load(name)
            except tts.TTSError as e:
                raise RequestError(502, f"TTS: {e}") from e
            self._send_audio(pcm, _audio_format(query))
            return
        if path.startswith(commands.URL_PREFIX):
            name = path.removeprefix(commands.URL_PREFIX)
            if name not in commands.REPLIES:
                raise RequestError(404, f"tidak ada jawaban template {name}")
            try:
                pcm = commands.load(name)
            except tts.TTSError as e:
                raise RequestError(502, f"TTS: {e}") from e
            self._send_audio(pcm, _audio_format(query))
            return
        if path == intro.AUDIO_URL:
            self._send_audio(self._intro()[1], _audio_format(query))
            return
        raise RequestError(404, f"tidak ada {path}")

    def _with_voice(self, data: dict) -> dict:
        """Beri audio_url tiap pemberitahuan yang perlu dibacakan, tandai status Mode Suara, dan
        (saat mode aktif) daftar pesan status. Presensi dibuka dan deadline tugas selalu
        dibacakan; jenis lain hanya saat Mode Suara aktif."""
        settings = voice_mode.load()
        data["voice_mode"] = settings["enabled"]
        data["language"] = lang.current()  # firmware 1.5+: label di layar ikut bahasa ini
        speed = voice_mode.SPEEDS[settings["speed"]]
        for alert in data.get("alerts", []):
            spoken = settings["enabled"] or alert.get("kind") in voice_mode.ALWAYS_SPOKEN
            if spoken and alert.get("speech"):
                key = self.server.speech.add(clean_speech(alert["speech"]), speed)
                alert["audio_url"] = f"/v1/speech/{key}"
        if settings["enabled"]:
            data["voice_clips"] = clips.urls()
        return data

    def _speech(self, key: str, fmt: str) -> None:
        item = self.server.speech.get(key)
        if item is None:
            raise RequestError(404, "suara pemberitahuan tidak ada atau sudah usang")
        with item["lock"]:
            if item["pcm"] is None:
                try:
                    item["pcm"] = b"".join(tts.stream(item["text"], speed=item["speed"]))
                except tts.TTSError as e:
                    raise RequestError(502, f"TTS: {e}") from e
        voice_mode.record("alert")
        self._send_audio(item["pcm"], fmt)

    def _intro(self) -> tuple[dict, bytes]:
        try:
            return intro.load()
        except tts.TTSError as e:
            raise RequestError(502, f"TTS: {e}") from e

    def _post(self, path: str, query: dict) -> None:
        if not path.startswith("/v1/"):
            self.server.web.handle(self, "POST", path, query)
            return
        self._authorize()
        if path != "/v1/ask":
            raise RequestError(404, f"tidak ada {path}")
        # Disiapkan sebelum badan dibaca: berjalan selagi perangkat masih mengirim rekaman.
        prepared = self.server.agent.prepare(query.get("new", ["0"])[0] in {"1", "true"})
        self._ask(self._read_body(), prepared)

    def _authorize(self) -> None:
        if self.server.token is not None:
            given = self.headers.get("Authorization", "").encode()
            if not hmac.compare_digest(given, f"Bearer {self.server.token}".encode()):
                raise RequestError(401, "token perangkat salah atau tidak ada")
        device_status.record(self.headers, urlsplit(self.path).path)  # untuk dashboard

    def _read_body(self) -> bytes:
        if "chunked" in self.headers.get("Transfer-Encoding", "").lower():
            return self._read_chunked()
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1
        if length < 0:  # read(-1) akan menunggu sampai koneksi ditutup
            raise RequestError(400, "Content-Length tidak valid")
        if length > MAX_BODY_BYTES:
            raise RequestError(413, f"rekaman melebihi {MAX_BODY_BYTES // 1024 // 1024} MB")
        body = self.rfile.read(length)
        if len(body) < length:
            raise RequestError(400, "rekaman terpotong")
        return body

    def _read_chunked(self) -> bytes:
        body = bytearray()
        while True:
            try:
                size = int(self.rfile.readline(64).split(b";")[0].strip(), 16)
            except ValueError:
                size = -1
            if size < 0:
                raise RequestError(400, "chunk tidak valid")
            if size == 0:
                while self.rfile.readline(1024) not in (b"\r\n", b"\n", b""):
                    pass  # trailer
                return bytes(body)
            if len(body) + size > MAX_BODY_BYTES:
                raise RequestError(413, f"rekaman melebihi {MAX_BODY_BYTES // 1024 // 1024} MB")
            chunk = self.rfile.read(size)
            if len(chunk) < size:
                raise RequestError(400, "rekaman terpotong")
            body += chunk
            self.rfile.readline(8)  # CRLF penutup chunk

    def _ask(self, body: bytes, prepared: Future) -> None:
        content_type = self.headers.get_content_type()
        timing: dict[str, float] = {}
        if content_type == "application/json":
            try:
                question = str(json.loads(body or b"{}").get("text") or "").strip()
            except (ValueError, AttributeError):
                raise RequestError(400, 'badan JSON harus {"text": "..."}') from None
            if not question:
                raise RequestError(400, "text kosong")
        else:
            started = time.time()
            try:
                question = (
                    stt.transcribe_file(body, "audio.wav")
                    if content_type in WAV_TYPES
                    else stt.transcribe_pcm(body)
                )
            except stt.STTError as e:
                raise RequestError(502, f"STT: {e}") from e
            timing["stt"] = round(time.time() - started, 2)
            if not question:
                log.info("[device] tidak ada ucapan (%d byte)", len(body))
                self._json(
                    200,
                    {
                        "status": "no_speech",
                        "question": "",
                        "speech": "",
                        "screen": NO_SPEECH_SCREEN,
                        "audio_url": None,
                        "timing": timing,
                    },
                )
                return

        started = time.time()
        # Perintah setelan ("aktifkan mode suara", "bicara lebih cepat") dijawab di sini: hasilnya
        # selalu kalimat yang sama, jadi tidak perlu token LLM maupun kuota TTS. `prepared`
        # dibiarkan selesai sendiri dan giliran ini tidak disimpan ke memory: bukan percakapan.
        reply = commands.handle(question)
        if reply is not None:
            timing["agent"] = round(time.time() - started, 2)
            self._template_reply(question, reply, timing)
            return

        from edupad.agent.assistant import LLMError

        try:
            result = self.server.agent.answer(question, prepared)
        except LLMError as e:
            raise RequestError(502, f"agent: {e}") from e
        timing["agent"] = round(time.time() - started, 2)
        device_status.record(self.headers, "/v1/ask", latency_s=sum(timing.values()))
        audio = self.server.audio.add(result["speech"]) if result["speech"] else None
        if audio and self.headers.get("X-Firmware"):
            # Perangkat selalu meminta suaranya setelah menampilkan layar: TTS dimulai sekarang,
            # bukan saat permintaan itu tiba. curl/tes (tanpa X-Firmware) tetap baru disuarakan
            # saat diminta, jadi tidak memakai kuota TTS.
            audio.start()
        audio_id = audio.id if audio else None
        log.info("[device] %r -> %r %s", question, result["speech"][:80], timing)
        voice = voice_mode.enabled()  # dibaca setelah menjawab: bisa baru diubah lewat suara
        if voice and audio_id:
            voice_mode.record("answer")
        self._json(
            200,
            {
                "status": "ok",
                "question": question,
                "speech": result["speech"],
                "screen": result["screen"],
                "audio_url": f"/v1/audio/{audio_id}" if audio_id else None,
                "timing": timing,
                "voice_mode": voice,
                "language": lang.current(),  # bisa baru diganti lewat suara di pertanyaan ini
                **({"voice_clips": clips.urls()} if voice else {}),
            },
        )

    def _template_reply(self, question: str, reply: dict, timing: dict) -> None:
        """Jawaban perintah setelan: bentuknya sama dengan jawaban agent, tapi `audio_url`-nya
        menunjuk PCM yang sudah tersimpan di disk."""
        device_status.record(self.headers, "/v1/ask", latency_s=sum(timing.values()))
        log.info("[device] %r -> template %s %s", question, reply["reply"], timing)
        voice = voice_mode.enabled()  # dibaca setelah setelan diterapkan
        if voice:
            voice_mode.record("answer")
        self._json(
            200,
            {
                "status": "ok",
                "question": question,
                "speech": reply["speech"],
                "screen": reply["screen"],
                "audio_url": reply["audio_url"],
                "timing": timing,
                "voice_mode": voice,
                "language": lang.current(),  # bisa baru diganti lewat suara di pertanyaan ini
                **({"voice_clips": clips.urls()} if voice else {}),
            },
        )

    def _audio(self, audio_id: str, fmt: str) -> None:
        item = self.server.audio.get(audio_id)
        if item is None:
            raise RequestError(404, "audio tidak ada atau sudah diganti jawaban baru")
        if item.pcm is not None:  # sudah selesai disuarakan: utuh, dengan Content-Length
            self._send_audio(item.pcm, fmt)
            return
        item.start()
        chunks = item.read()
        try:
            first = next(chunks, b"")  # error kuota/kunci muncul di sini, sebelum header terkirim
            if fmt == "wav":
                self._send_audio(first + b"".join(chunks), fmt)
                return
        except tts.TTSError as e:
            raise RequestError(502, f"TTS: {e}") from e
        self._stream_audio(itertools.chain([first], chunks), fmt)

    def _stream_audio(self, chunks: Iterator[bytes], fmt: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("X-Audio-Format", adpcm.FORMAT if fmt == "adpcm" else AUDIO_FORMAT)
        self.send_header("Transfer-Encoding", "chunked")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self._streaming = True
        encoder = adpcm.Encoder() if fmt == "adpcm" else None
        try:
            for chunk in chunks:
                self._write_chunk(encoder.feed(chunk) if encoder else chunk)
            if encoder:
                self._write_chunk(encoder.flush())
        except tts.TTSError as e:
            # Header 200 sudah terkirim: putus tanpa chunk penutup agar perangkat tahu audio tidak utuh.
            log.warning("[!] TTS terputus di tengah audio: %s", e)
            self.close_connection = True
            return
        except (BrokenPipeError, ConnectionResetError, TimeoutError) as e:
            # Pemutaran dihentikan di perangkat: sintesis tetap selesai di latar (Synthesis), jadi
            # putar ulang tidak memanggil TTS lagi.
            log.info("[device] pemutaran dihentikan (%s), audio tetap disimpan", e)
            self.close_connection = True
            return
        self.wfile.write(b"0\r\n\r\n")

    def _write_chunk(self, data: bytes) -> None:
        if data:
            self.wfile.write(b"%X\r\n%s\r\n" % (len(data), data))

    def _send_audio(self, pcm: bytes, fmt: str) -> None:
        kind = "application/octet-stream"
        if fmt == "wav":
            data, kind, audio_format = tts.to_wav(pcm), "audio/wav", None
        elif fmt == "adpcm":
            data, audio_format = _adpcm(pcm), adpcm.FORMAT
        else:
            data, audio_format = pcm, AUDIO_FORMAT
        self.send_response(200)
        self.send_header("Content-Type", kind)
        if audio_format:
            self.send_header("X-Audio-Format", audio_format)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, status: int, body: dict) -> None:
        data = json.dumps(body, ensure_ascii=False).encode()
        if status >= 400:
            self.close_connection = True  # badan permintaan mungkin belum terbaca seluruhnya
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        if self.close_connection:
            self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(data)


class _DiscardBody:
    """Pengganti wfile setelah header HEAD terkirim: badan respons tidak ditulis."""

    def write(self, data: bytes) -> int:
        return len(data)

    def flush(self) -> None:
        pass


def publicly_reachable(host: str, settings: Settings) -> bool:
    """Bisa dicapai dari internet: mendengarkan di jaringan, atau di belakang reverse proxy
    publik (EDUPAD_PUBLIC_URL bukan localhost) walau server sendiri hanya di 127.0.0.1."""
    return host not in LOCAL_HOSTS or urlsplit(settings.public_url).hostname not in LOCAL_HOSTS


def run(host: str, port: int) -> int:
    settings = get_settings()
    if not settings.device_token and publicly_reachable(host, settings):
        log.error(
            "[x] EDUPAD_DEVICE_TOKEN belum diisi di .env; wajib bila server bisa diakses "
            'dari internet. Buat dengan: python -c "import secrets; print(secrets.token_urlsafe(32))"'
        )
        return 1
    for name, value in (
        ("API_KEY_AI", settings.llm_api_key),
        ("API_KEY_GROQ", settings.groq_api_key),
        ("API_KEY_ElevenLabs", settings.elevenlabs_api_key),
    ):
        if not value:
            log.warning("[!] %s belum diisi di .env", name)
    if len(settings.elevenlabs_accounts) > 1:  # cadangan saat kuota akun pertama habis
        log.info("[ok] %d akun ElevenLabs dipakai berurutan", len(settings.elevenlabs_accounts))
    server = EduPadServer((host, port), settings.device_token)
    log.info(
        "[ok] EduPad server di http://%s:%d (token %s)",
        host,
        server.server_address[1],
        "aktif" if settings.device_token else "TIDAK aktif, hanya lokal",
    )
    if settings.google_client_id and settings.google_client_secret:
        log.info(
            "[ok] login Google aktif; redirect URI: %s/auth/google/callback", settings.public_url
        )
    else:
        log.warning("[!] GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET belum diisi: login web nonaktif")
    if not (WEB_DIST_DIR / "index.html").is_file():
        log.warning("[!] halaman web belum di-build (cd web && npm install && npm run build)")
    signal.signal(signal.SIGTERM, _stop)  # systemctl stop: simpan giliran yang tertunda dulu
    try:
        server.serve_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        server.server_close()
        log.info("[ok] server berhenti")
    return 0


def _stop(signum, frame) -> None:
    raise SystemExit(0)
