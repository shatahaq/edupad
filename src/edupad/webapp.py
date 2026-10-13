"""Web EduPad: login Google, API untuk halaman React, dan file hasil build (web/dist).

Rute (selain /v1/* milik perangkat ESP32, lihat server.py):

    GET  /auth/google/login      ke layar login Google (`?consent=1`: minta izin ulang)
    GET  /auth/google/callback   kembali dari Google; cookie sesi dipasang, lalu ke /dashboard
    POST /auth/logout            akhiri sesi browser (izin Classroom tetap untuk sinkronisasi)
    GET  /api/me                 profil pengguna yang login (401 bila belum)
    GET  lainnya                 halaman React; rute yang tidak dikenal -> index.html (SPA)

Login gagal kembali ke `/?error=<kode>` agar halaman depan bisa menampilkan pesannya.
"""

from __future__ import annotations

import hmac
import json
import logging
import mimetypes
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

from edupad.config import CLASSROOM_DIR, WEB_DIST_DIR, Settings, get_settings
from edupad.core.files import read_json
from edupad.google import oauth
from edupad.google.accounts import (
    STATUS_REAUTH,
    AccountStore,
    SessionStore,
    edupad_user_id,
    has_classroom,
    usable_refresh_token,
)

log = logging.getLogger(__name__)

SESSION_COOKIE = "edupad_session"
LOGIN_COOKIE = "edupad_login"  # state OAuth: mengikat callback ke browser yang memulai login
LOGIN_TTL = 600  # detik untuk menyelesaikan layar login Google
MAX_PENDING_LOGINS = 500
CSP = (
    "default-src 'self'; img-src 'self' data: https://*.googleusercontent.com; "
    "style-src 'self'; script-src 'self'; font-src 'self'; connect-src 'self'; "
    "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
)


def start_classroom_sync(email: str) -> None:
    """Sinkronisasi Classroom pertama di latar belakang agar data siap setelah login."""
    from edupad.collectors import classroom

    def sync() -> None:
        try:
            classroom.run(email=email)
        except Exception:  # noqa: BLE001 - thread latar belakang tidak boleh diam-diam gagal
            log.exception("[x] sinkronisasi Classroom %s gagal", email)

    threading.Thread(target=sync, name="classroom-sync", daemon=True).start()


class WebApp:
    def __init__(
        self,
        settings: Callable[[], Settings] = get_settings,
        accounts: AccountStore | None = None,
        sessions: SessionStore | None = None,
        dist_dir: Path = WEB_DIST_DIR,
        classroom_dir: Path = CLASSROOM_DIR,
        on_login: Callable[[str], None] = start_classroom_sync,
    ):
        self._settings = settings  # dibaca per permintaan: perubahan .env berlaku tanpa restart
        self.accounts = accounts or AccountStore()
        self.sessions = sessions or SessionStore()
        self.dist_dir, self.classroom_dir, self.on_login = dist_dir, classroom_dir, on_login
        self._pending: OrderedDict[str, tuple[oauth.LoginRequest, float]] = OrderedDict()
        self._lock = threading.Lock()

    # ------------------------------ routing ----------------------------------
    def handle(self, h: BaseHTTPRequestHandler, method: str, path: str, query: dict) -> None:
        routes = {
            ("GET", "/auth/google/login"): lambda: self._login(h, query),
            ("GET", "/auth/google/callback"): lambda: self._callback(h, query),
            ("POST", "/auth/logout"): lambda: self._logout(h),
            ("GET", "/api/me"): lambda: self._me(h),
        }
        route = routes.get((method, path))
        if route:
            route()
        elif path.startswith(("/api/", "/auth/")):
            known = any(p == path for _, p in routes)
            self._json(
                h,
                405 if known else 404,
                {"error": "metode tidak didukung" if known else "tidak ada"},
            )
        elif method == "GET":
            self._static(h, path)
        else:
            self._json(h, 405, {"error": "metode tidak didukung"})

    # ------------------------------ login ------------------------------------
    def _login(self, h: BaseHTTPRequestHandler, query: dict) -> None:
        settings = self._settings()
        client = oauth.Client.from_settings(settings)
        if client is None:
            log.error("[x] login Google: GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET belum diisi")
            self._redirect(h, "/?error=not_configured")
            return
        login = oauth.new_login(consent=_first(query, "consent") == "1")
        with self._lock:
            now = time.monotonic()
            for state in [s for s, (_, t) in self._pending.items() if now - t > LOGIN_TTL]:
                del self._pending[state]
            self._pending[login.state] = (login, now)
            while len(self._pending) > MAX_PENDING_LOGINS:
                self._pending.popitem(last=False)
        cookie = self._cookie(settings, LOGIN_COOKIE, login.state, LOGIN_TTL, path="/auth/google")
        self._redirect(h, oauth.authorization_url(client, login), [cookie])

    def _take_login(self, state: str | None) -> oauth.LoginRequest | None:
        if not state:
            return None
        with self._lock:
            entry = self._pending.pop(state, None)
        if entry is None or time.monotonic() - entry[1] > LOGIN_TTL:
            return None
        return entry[0]

    def _callback(self, h: BaseHTTPRequestHandler, query: dict) -> None:
        settings = self._settings()
        clear_login = self._cookie(settings, LOGIN_COOKIE, "", 0, path="/auth/google")
        error = _first(query, "error")
        if error:
            # access_denied: pengguna menekan Batal di layar Google
            self._fail(
                h, "access_denied" if error == "access_denied" else "google_error", [clear_login]
            )
            return
        state = _first(query, "state")
        login = self._take_login(state)
        browser_state = self._cookies(h).get(LOGIN_COOKIE)
        if not (login and browser_state and hmac.compare_digest(browser_state, state or "")):
            self._fail(h, "state", [clear_login])
            return
        client = oauth.Client.from_settings(settings)
        code = _first(query, "code")
        if client is None or not code:
            self._fail(h, "not_configured" if client is None else "google_error", [clear_login])
            return
        try:
            tokens = oauth.exchange_code(client, code, login.verifier)
            claims = oauth.id_token_claims(tokens.id_token, client, login.nonce)
        except oauth.GoogleAuthError as e:
            log.warning("[!] login Google gagal: %s", e)
            self._fail(h, "google_error", [clear_login])
            return
        existing = self.accounts.get(claims["sub"])
        if not (tokens.refresh_token or usable_refresh_token(existing)) and not login.consent:
            # Tidak ada refresh token yang bisa dipakai (file akun hilang, atau token lama
            # kedaluwarsa/dicabut): Google hanya mengirim yang baru lewat layar izin, jadi
            # ulangi sekali dengan prompt=consent.
            self._redirect(h, "/auth/google/login?consent=1", [clear_login])
            return
        user_id = edupad_user_id(claims["email"], claims["sub"], settings)
        account = self.accounts.save_login(claims, tokens, user_id)
        session = self.sessions.create(account["sub"])
        log.info(
            "[web] login %s (Classroom %s)",
            account["email"],
            "ya" if has_classroom(account) else "tidak",
        )
        if has_classroom(account):
            self.on_login(account["email"])
        cookie = self._cookie(settings, SESSION_COOKIE, session, self.sessions.lifetime)
        self._redirect(h, "/dashboard", [cookie, clear_login])

    def _logout(self, h: BaseHTTPRequestHandler) -> None:
        settings = self._settings()
        if not self._same_origin(h, settings):
            self._json(h, 403, {"error": "asal permintaan tidak diizinkan"})
            return
        self.sessions.delete(self._cookies(h).get(SESSION_COOKIE))
        self._json(h, 200, {"ok": True}, [self._cookie(settings, SESSION_COOKIE, "", 0)])

    # ------------------------------- API -------------------------------------
    def _me(self, h: BaseHTTPRequestHandler) -> None:
        sub = self.sessions.get(self._cookies(h).get(SESSION_COOKIE))
        account = self.accounts.get(sub) if sub else None
        if not account:
            self._json(h, 401, {"error": "belum login"})
            return
        synced = read_json(self.classroom_dir / f"{account['sub']}.json")
        self._json(
            h,
            200,
            {
                "name": account.get("name"),
                "email": account.get("email"),
                "picture": account.get("picture"),
                "classroom": {
                    "granted": has_classroom(account),
                    "reauth_required": account.get("status") == STATUS_REAUTH,
                    "courses": len(synced.get("kelas", [])) if synced else None,
                    "synced_at": synced.get("diperbarui"),
                },
            },
        )

    # ------------------------------ static -----------------------------------
    def _static(self, h: BaseHTTPRequestHandler, path: str) -> None:
        index = self.dist_dir / "index.html"
        if not index.is_file():
            self._send(
                h,
                503,
                b"Halaman web belum di-build. Jalankan: cd web && npm install && npm run build\n",
                "text/plain; charset=utf-8",
            )
            return
        relative = unquote(path).lstrip("/")
        root = self.dist_dir.resolve()
        try:
            target = (root / relative).resolve()
            target.relative_to(root)  # tolak ../ keluar dari web/dist
            is_file = target.is_file()
        except (ValueError, OSError):
            self._json(h, 404, {"error": "tidak ada"})
            return
        if not is_file:
            if "." in PurePosixPath(relative).name:  # file aset yang tidak ada, bukan rute halaman
                self._json(h, 404, {"error": "tidak ada"})
                return
            target = root / "index.html"  # "/" dan rute React, mis. /dashboard
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in {
            "application/javascript",
            "image/svg+xml",
        }:
            content_type += "; charset=utf-8"
        # Aset Vite bernama hash isi: aman di-cache selamanya. index.html selalu dicek ulang.
        cache = (
            "public, max-age=31536000, immutable" if relative.startswith("assets/") else "no-cache"
        )
        headers = {"Cache-Control": cache}
        if target.suffix == ".html":
            headers["Content-Security-Policy"] = CSP
        self._send(h, 200, target.read_bytes(), content_type, headers)

    # ------------------------------ helpers ----------------------------------
    @staticmethod
    def _cookies(h: BaseHTTPRequestHandler) -> dict[str, str]:
        jar = SimpleCookie()
        try:
            jar.load(h.headers.get("Cookie", ""))
        except CookieError:
            return {}
        return {name: morsel.value for name, morsel in jar.items()}

    @staticmethod
    def _cookie(settings: Settings, name: str, value: str, max_age: int, path: str = "/") -> str:
        parts = [
            f"{name}={value}",
            f"Path={path}",
            f"Max-Age={max_age}",
            "HttpOnly",
            "SameSite=Lax",
        ]
        if settings.public_url.startswith("https://"):
            parts.append("Secure")
        return "; ".join(parts)

    @staticmethod
    def _same_origin(h: BaseHTTPRequestHandler, settings: Settings) -> bool:
        """Anti-CSRF untuk POST: browser selalu mengirim Origin; klien non-browser boleh tanpa."""
        origin = h.headers.get("Origin")
        if not origin:
            return True
        public = urlsplit(settings.public_url)
        return origin.rstrip("/") == f"{public.scheme}://{public.netloc}"

    def _fail(self, h: BaseHTTPRequestHandler, code: str, cookies: list[str]) -> None:
        self._redirect(h, f"/?error={code}", cookies)

    def _redirect(
        self, h: BaseHTTPRequestHandler, location: str, cookies: list[str] | None = None
    ) -> None:
        self._send(h, 302, b"", None, {"Location": location, "Cache-Control": "no-store"}, cookies)

    def _json(
        self, h: BaseHTTPRequestHandler, status: int, body: dict, cookies: list[str] | None = None
    ) -> None:
        data = json.dumps(body, ensure_ascii=False).encode()
        self._send(
            h,
            status,
            data,
            "application/json; charset=utf-8",
            {"Cache-Control": "no-store"},
            cookies,
        )

    @staticmethod
    def _send(
        h: BaseHTTPRequestHandler,
        status: int,
        data: bytes,
        content_type: str | None,
        headers: dict[str, str] | None = None,
        cookies: list[str] | None = None,
    ) -> None:
        # Badan POST tidak pernah dibaca rute web: tutup koneksi agar sisa badan tidak
        # terbaca sebagai permintaan berikutnya.
        if h.command == "POST" or status >= 400:
            h.close_connection = True
        h.send_response(status)
        if content_type:
            h.send_header("Content-Type", content_type)
        h.send_header("Content-Length", str(len(data)))
        h.send_header("X-Content-Type-Options", "nosniff")
        h.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        h.send_header("X-Frame-Options", "DENY")
        for name, value in (headers or {}).items():
            h.send_header(name, value)
        for cookie in cookies or []:
            h.send_header("Set-Cookie", cookie)
        if h.close_connection:
            h.send_header("Connection", "close")
        h.end_headers()
        h.wfile.write(data)


def _first(query: dict, name: str) -> str | None:
    values = query.get(name)
    return values[0] if values else None
