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
   ElevenLabs mengirimnya sehingga perangkat bisa langsung memutar. Hanya suara jawaban
   terakhir yang disimpan (jawaban baru menimpanya); putar ulang lewat URL yang sama atau
   GET /v1/audio/latest diambil dari simpanan tanpa memakai kuota TTS. `?format=wav` untuk
   didengar di laptop.

Semua permintaan selain GET /v1/health wajib membawa header
`Authorization: Bearer <EDUPAD_DEVICE_TOKEN>`.

Path di luar /v1/ dilayani web EduPad (login Google, /api, halaman React): lihat webapp.py.
"""

from __future__ import annotations

import hmac
import itertools
import json
import logging
import secrets
import signal
import threading
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from edupad.agent.formatting import fit_screen
from edupad.config import DEEPSEEK_URL, WEB_DIST_DIR, Settings, get_settings
from edupad.core import http_pool
from edupad.voice import stt, tts
from edupad.webapp import WebApp

log = logging.getLogger(__name__)

MAX_BODY_BYTES = 5 * 1024 * 1024  # rekaman 120 detik = 3,8 MB
READ_TIMEOUT = 30  # detik tanpa data dari perangkat sebelum koneksi diputus
AUDIO_FORMAT = f"pcm_s16le;rate={tts.SAMPLE_RATE};channels=1"
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
    from edupad.agent.assistant import open_memory

    try:
        memory = open_memory(new_session=new_session)
        if memory:
            memory.prefetch()
        return memory
    except Exception as e:  # noqa: BLE001 - tanpa memory, agent tetap bisa menjawab
        log.warning("[!] memory tidak bisa dimuat, menjawab tanpa memory: %s", e)
        return None


def _logged(job: Callable[[], None]) -> None:
    try:
        job()
    except Exception:  # noqa: BLE001 - worker latar belakang tidak boleh diam-diam gagal
        log.exception("[x] giliran gagal disimpan ke memory")


class AudioStore:
    """Suara jawaban terakhir: teksnya, lalu PCM-nya setelah pertama kali disuarakan.

    Jawaban baru menimpa yang lama. Putar ulang memakai PCM yang tersimpan sehingga kuota TTS
    hanya terpakai sekali per jawaban. `lock` membuat dua permintaan untuk jawaban yang belum
    disuarakan tidak memanggil ElevenLabs dua kali: yang kedua menunggu lalu memakai PCM-nya.
    """

    LATEST = "latest"

    def __init__(self):
        self._latest: dict | None = None
        self._lock = threading.Lock()

    def add(self, text: str) -> str:
        audio_id = secrets.token_urlsafe(9)
        with self._lock:
            self._latest = {"id": audio_id, "text": text, "pcm": None, "lock": threading.Lock()}
        return audio_id

    def get(self, audio_id: str) -> dict | None:
        with self._lock:
            item = self._latest
        if item and audio_id in (item["id"], self.LATEST):
            return item
        return None

    def set_pcm(self, audio_id: str, pcm: bytes) -> None:
        with self._lock:
            if self._latest and self._latest["id"] == audio_id:
                self._latest["pcm"] = pcm


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
            self._audio(path.removeprefix("/v1/audio/"), wav=query.get("format") == ["wav"])
            return
        raise RequestError(404, f"tidak ada {path}")

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
        if self.server.token is None:
            return
        given = self.headers.get("Authorization", "").encode()
        if not hmac.compare_digest(given, f"Bearer {self.server.token}".encode()):
            raise RequestError(401, "token perangkat salah atau tidak ada")

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
        from edupad.agent.assistant import LLMError

        try:
            result = self.server.agent.answer(question, prepared)
        except LLMError as e:
            raise RequestError(502, f"agent: {e}") from e
        timing["agent"] = round(time.time() - started, 2)
        audio_id = self.server.audio.add(result["speech"]) if result["speech"] else None
        log.info("[device] %r -> %r %s", question, result["speech"][:80], timing)
        self._json(
            200,
            {
                "status": "ok",
                "question": question,
                "speech": result["speech"],
                "screen": result["screen"],
                "audio_url": f"/v1/audio/{audio_id}" if audio_id else None,
                "timing": timing,
            },
        )

    def _audio(self, audio_id: str, wav: bool) -> None:
        item = self.server.audio.get(audio_id)
        if item is None:
            raise RequestError(404, "audio tidak ada atau sudah diganti jawaban baru")
        with item["lock"]:
            if item["pcm"] is not None:
                self._send_audio(item["pcm"], wav)
                return
            chunks = tts.stream(item["text"])
            try:
                first = next(chunks, b"")  # error kuota/kunci muncul di sini, sebelum header terkirim
                if wav:
                    pcm = first + b"".join(chunks)
                    self.server.audio.set_pcm(item["id"], pcm)
                    self._send_audio(pcm, wav=True)
                else:
                    self._stream_audio(item["id"], first, chunks)
            except tts.TTSError as e:
                raise RequestError(502, f"TTS: {e}") from e
            finally:
                getattr(
                    chunks, "close", lambda: None
                )()  # tutup koneksi ElevenLabs bila berhenti di tengah

    def _stream_audio(self, audio_id: str, first: bytes, chunks) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("X-Audio-Format", AUDIO_FORMAT)
        self.send_header("Transfer-Encoding", "chunked")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self._streaming = True
        sent, carry, device_gone = [], b"", False
        try:
            for chunk in itertools.chain([first], chunks):
                data = carry + chunk
                cut = len(data) - len(data) % tts.SAMPLE_WIDTH  # jangan memotong satu sampel
                data, carry = data[:cut], data[cut:]
                if not data:
                    continue
                sent.append(data)
                if device_gone:
                    continue
                try:
                    self.wfile.write(b"%X\r\n%s\r\n" % (len(data), data))
                except (BrokenPipeError, ConnectionResetError, TimeoutError) as e:
                    # Pemutaran dihentikan di perangkat: sisa audio tetap diambil (kuota sudah
                    # terpakai untuk seluruh teks) supaya putar ulang tidak memanggil TTS lagi.
                    log.info("[device] pemutaran dihentikan (%s), audio tetap disimpan", e)
                    device_gone = True
                    self.close_connection = True
        except tts.TTSError as e:
            # Header 200 sudah terkirim: putus tanpa chunk penutup agar perangkat tahu audio tidak utuh.
            log.warning("[!] TTS terputus di tengah audio: %s", e)
            self.close_connection = True
            return
        self.server.audio.set_pcm(audio_id, b"".join(sent))
        if not device_gone:
            self.wfile.write(b"0\r\n\r\n")

    def _send_audio(self, pcm: bytes, wav: bool) -> None:
        data = tts.to_wav(pcm) if wav else pcm
        self.send_response(200)
        self.send_header("Content-Type", "audio/wav" if wav else "application/octet-stream")
        if not wav:
            self.send_header("X-Audio-Format", AUDIO_FORMAT)
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
