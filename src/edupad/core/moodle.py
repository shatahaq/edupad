"""Klien HTTP kelas.usu.ac.id memakai cookie sesi tersimpan (tanpa browser).

Hanya memanggil fungsi AJAX yang juga dipakai halaman web Moodle sendiri;
web service mobile/mod_assign dimatikan di server USU.
"""

from __future__ import annotations

import re
import time
from html import unescape

from edupad.config import MOODLE_SESSION_FILE, MOODLE_URL, REQUEST_DELAY, REQUEST_TIMEOUT
from edupad.core.session import cookie_session, persist_cookie_updates
from edupad.errors import LoginRequired

_LOGIN_ERRORS = {
    "servicerequireslogin",
    "requireloginerror",
    "sessionexpired",
    "invalidsesskey",
    "requirelogin",
}
SSO_TOKEN_COOKIE = "ssotok"  # token sso.usu.ac.id di domain .usu.ac.id


class MoodleError(RuntimeError):
    pass


class MoodleClient:
    def __init__(self, sesskey: str | None = None):
        self.http = cookie_session(MOODLE_SESSION_FILE)
        self._sesskey = sesskey

    @property
    def sesskey(self) -> str:
        if self._sesskey is None:
            self._sesskey = self.fetch_sesskey()
        return self._sesskey

    def fetch_sesskey(self) -> str:
        r = self.http.get(
            f"{MOODLE_URL}/my/courses.php", timeout=REQUEST_TIMEOUT, allow_redirects=False
        )
        if r.status_code in (301, 302, 303) or "/login/" in r.url:
            raise LoginRequired(f"diarahkan ke {r.headers.get('location', 'halaman login')}")
        m = re.search(r'"sesskey":"(\w+)"', r.text)
        if not m:
            raise LoginRequired("sesskey tidak ditemukan (kemungkinan halaman login)")
        self._sesskey = m.group(1)
        return self._sesskey

    def sso_relogin(self) -> None:
        """Buat sesi Moodle baru dari token SSO USU yang masih berlaku, tanpa password.

        kelas.usu.ac.id/auth/jwtsso membaca cookie ssotok lalu langsung membuat
        MoodleSession baru; bila token habis, diarahkan ke form login sso.usu.ac.id.
        """
        if not self.sso_token_expiry():
            raise LoginRequired("token SSO USU tidak ada atau sudah habis")
        self.http.cookies.clear("kelas.usu.ac.id", "/", "MoodleSession")
        r = self.http.get(f"{MOODLE_URL}/auth/jwtsso/login.php", timeout=REQUEST_TIMEOUT)
        if not r.url.startswith(MOODLE_URL) or "/login/" in r.url:
            raise LoginRequired("token SSO USU ditolak (diarahkan ke form login)")
        self._sesskey = None
        self.fetch_sesskey()

    def sso_token_expiry(self) -> float | None:
        """Waktu kedaluwarsa token SSO (epoch), None bila tidak ada atau sudah lewat.

        Dibaca dari file sesi: cookie_session memuat cookie tanpa atribut expires.
        """
        from edupad.core.session import load_cookies

        expiry = max(
            (
                c.get("expires") or 0
                for c in load_cookies(MOODLE_SESSION_FILE).get("cookies", [])
                if c["name"] == SSO_TOKEN_COOKIE
            ),
            default=0,
        )
        return expiry if expiry > time.time() else None

    def call(self, method: str, args: dict | None = None):
        r = self.http.post(
            f"{MOODLE_URL}/lib/ajax/service.php?sesskey={self.sesskey}&info={method}",
            json=[{"index": 0, "methodname": method, "args": args or {}}],
            timeout=REQUEST_TIMEOUT,
            allow_redirects=False,
        )
        if r.status_code != 200:
            raise LoginRequired(f"HTTP {r.status_code} dari {method}")
        data = r.json()
        if isinstance(data, dict):  # error level request, mis. sesskey salah
            error = data.get("errorcode", "")
            raise (LoginRequired if error in _LOGIN_ERRORS else MoodleError)(f"{method}: {error}")
        result = data[0]
        if result.get("error"):
            exc = result.get("exception", {})
            error = exc.get("errorcode", "")
            raise (LoginRequired if error in _LOGIN_ERRORS else MoodleError)(
                f"{method}: {error} {exc.get('message', '')}".strip()
            )
        return result.get("data")

    def get_page(self, url: str) -> str:
        r = self.http.get(url, timeout=REQUEST_TIMEOUT)
        time.sleep(REQUEST_DELAY)
        if "/login/" in r.url or "jwtsso" in r.url:
            raise LoginRequired(f"diarahkan ke login saat membuka {url}")
        r.raise_for_status()
        return r.text

    def enrolled_courses(self) -> list[dict]:
        data = self.call(
            "core_course_get_enrolled_courses_by_timeline_classification",
            {"offset": 0, "limit": 0, "classification": "all", "sort": "fullname"},
        )
        return [
            {"id": str(c["id"]), "name": unescape(c["fullname"]).strip(), "url": c["viewurl"]}
            for c in data["courses"]
        ]

    def save_cookies(self) -> None:
        persist_cookie_updates(MOODLE_SESSION_FILE, self.http)
