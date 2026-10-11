"""Cookie sesi login & status sesi per layanan (Moodle, portal SATU).

Yang disimpan hanya cookie, bukan password.
"""

from __future__ import annotations

from pathlib import Path

import requests

from edupad.config import STATE_FILE
from edupad.core.files import now_iso, read_json, write_json
from edupad.core.notify import notify

MOODLE = "moodle"
SATU = "satu"

_SERVICE_LABEL = {MOODLE: "kelas.usu.ac.id", SATU: "portal SATU USU"}
_LOGIN_COMMAND = {MOODLE: "python -m edupad login", SATU: "python -m edupad schedule --login"}


def load_cookies(path: Path) -> dict:
    """{'saved_at', 'user_agent', 'cookies': [...]} atau {} bila belum login."""
    return read_json(path)


def save_cookies(path: Path, cookies: list[dict], user_agent: str | None = None, **extra) -> None:
    """Field tambahan (mis. login_at) dari penyimpanan sebelumnya dipertahankan."""
    data = load_cookies(path)
    data.update(
        extra, saved_at=now_iso(), cookies=cookies, user_agent=user_agent or data.get("user_agent")
    )
    write_json(path, data, private=True)


def cookie_session(path: Path) -> requests.Session:
    data = load_cookies(path)
    http = requests.Session()
    for c in data.get("cookies", []):
        http.cookies.set(c["name"], c["value"], domain=c["domain"], path=c.get("path", "/"))
    if data.get("user_agent"):
        http.headers["User-Agent"] = data["user_agent"]
    return http


def persist_cookie_updates(path: Path, http: requests.Session) -> None:
    """Samakan file cookie dengan cookie jar setelah request.

    Server bisa mengganti nilai, menambah, atau menghapus cookie (sesi portal SATU
    dipecah ke beberapa cookie yang jumlahnya berubah saat token diperbarui).
    Jar diisi dari file ini, jadi cookie yang hilang dari jar memang dihapus server.
    """
    data = load_cookies(path)
    saved = {(c["name"], c["domain"].lstrip(".")): c for c in data.get("cookies", [])}
    jar = {(c.name, c.domain.lstrip(".")): c for c in http.cookies}
    changed = saved.keys() != jar.keys()
    cookies = []
    for key, c in jar.items():
        entry = saved.get(key) or {
            "name": c.name,
            "domain": c.domain,
            "path": c.path or "/",
            "httpOnly": c.has_nonstandard_attr("HttpOnly"),
            "secure": c.secure,
            "sameSite": "Lax",
        }
        if entry.get("value") != c.value:
            entry["value"] = c.value
            changed = True
        entry["expires"] = c.expires or entry.get("expires", -1)
        cookies.append(entry)
    if changed:
        save_cookies(path, cookies, data.get("user_agent"))


def get_state(service: str) -> dict:
    return read_json(STATE_FILE).get(service, {})


def update_state(service: str, **fields) -> None:
    state = read_json(STATE_FILE)
    state.setdefault(service, {}).update(fields)
    write_json(STATE_FILE, state, private=True)


def report_login_expired(service: str, detected_by: str) -> None:
    """Kirim notifikasi hanya sekali per kejadian, bukan setiap cron berjalan."""
    if get_state(service).get("expired_since"):
        return
    update_state(service, expired_since=now_iso())
    note = (
        " Jadwal terakhir tetap dipakai; login ulang cukup saat KRS berubah."
        if service == SATU
        else ""
    )
    notify(
        f"⚠️ Sesi {_SERVICE_LABEL[service]} habis (terdeteksi oleh {detected_by}).{note} "
        f"Login ulang dengan: {_LOGIN_COMMAND[service]}"
    )


def report_login_ok(service: str) -> None:
    if get_state(service).get("expired_since"):
        notify(f"✅ Sesi {_SERVICE_LABEL[service]} aktif lagi.")
    update_state(service, expired_since=None, last_ok=now_iso())
