"""Menjaga sesi login tetap aktif (dijalankan tiap ~20 menit).

- kelas.usu.ac.id: sesi Moodle kedaluwarsa bila menganggur > 8 jam;
  core_session_touch (dipakai halaman Moodle sendiri) memperpanjangnya.
- Portal SATU: Keycloak (id.usu.ac.id) memutus sesi yang menganggur ~30 menit,
  sedangkan cookie SSO-nya berlaku ~14 hari. Tiap run melakukan login ulang
  senyap lewat cookie SSO agar batas menganggur ter-reset. Umur sesi dicatat
  saat berakhir untuk mengetahui batas maksimumnya.
"""

from __future__ import annotations

import base64
import json
import logging
from datetime import datetime

import requests

from edupad.config import MOODLE_SESSION_FILE, SATU_LOCK_FILE, SATU_SESSION_FILE, WIB
from edupad.core.lock import AlreadyRunning, wait_for_lock
from edupad.core.moodle import MoodleClient, MoodleError
from edupad.core.session import (
    MOODLE,
    SATU,
    cookie_session,
    get_state,
    load_cookies,
    persist_cookie_updates,
    report_login_expired,
    report_login_ok,
    update_state,
)
from edupad.errors import EXIT_ERROR, EXIT_LOGIN_REQUIRED, EXIT_OK, LoginRequired

log = logging.getLogger(__name__)


def _format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "tidak diketahui"
    hours, minutes = divmod(int(seconds) // 60, 60)
    return f"{hours} jam {minutes} menit" if hours else f"{minutes} menit"


# ------------------------------ Moodle ---------------------------------------
def _time_remaining(client: MoodleClient) -> int | None:
    try:
        return client.call("core_session_time_remaining")["timeremaining"]
    except MoodleError:
        return None  # server lama tidak menyediakan fungsi ini


def keep_moodle_alive() -> int:
    if not load_cookies(MOODLE_SESSION_FILE).get("cookies"):
        log.error("[x] Moodle: belum ada sesi. Jalankan: python -m edupad login")
        report_login_expired(MOODLE, "keepalive")
        return EXIT_LOGIN_REQUIRED

    client = MoodleClient(sesskey=get_state(MOODLE).get("sesskey"))
    try:
        try:
            before = _time_remaining(client)
        except LoginRequired:
            client.fetch_sesskey()  # sesskey cache basi setelah login ulang
            before = _time_remaining(client)
        client.call("core_session_touch")
        after = _time_remaining(client)
        if after is not None and after <= 0:
            raise LoginRequired("sisa waktu sesi 0")
    except LoginRequired as e:
        log.error("[x] Moodle: sesi habis (%s). Login ulang: python -m edupad login", e)
        update_state(MOODLE, sesskey=None)
        report_login_expired(MOODLE, "keepalive")
        return EXIT_LOGIN_REQUIRED
    except (requests.RequestException, MoodleError, ValueError) as e:
        log.warning("[!] Moodle: keep-alive gagal, bukan karena sesi: %s", e)  # tanpa alarm
        return EXIT_ERROR

    client.save_cookies()
    report_login_ok(MOODLE)
    update_state(MOODLE, sesskey=client.sesskey, timeout_seconds=after)
    log.info(
        "[ok] Moodle: sesi aktif. Sisa sebelum touch: %s, setelah: %s",
        _format_duration(before),
        _format_duration(after),
    )
    return EXIT_OK


# ------------------------------ portal SATU ----------------------------------
def _token_expiry(token: str | None) -> str | None:
    """Waktu kedaluwarsa access token (JWT) untuk log; tanpa verifikasi tanda tangan."""
    try:
        payload = json.loads(base64.urlsafe_b64decode(token.split(".")[1] + "=="))
        return datetime.fromtimestamp(payload["exp"], WIB).strftime("%H:%M WIB")
    except (AttributeError, IndexError, KeyError, ValueError):
        return None


def _session_age() -> str:
    login_at = load_cookies(SATU_SESSION_FILE).get("login_at")
    if not login_at:
        return "tidak diketahui"
    return _format_duration((datetime.now(WIB) - datetime.fromisoformat(login_at)).total_seconds())


def keep_satu_alive() -> int:
    try:
        with wait_for_lock(SATU_LOCK_FILE):
            return _keep_satu_alive()
    except AlreadyRunning as e:
        log.warning("[!] SATU: %s terlalu lama, keep-alive dilewati", e)
        return EXIT_ERROR


def _keep_satu_alive() -> int:
    from edupad.collectors.schedule import silent_relogin

    if not load_cookies(SATU_SESSION_FILE).get("cookies"):
        log.info("[-] SATU: belum ada sesi, dilewati (login: python -m edupad schedule --login)")
        return EXIT_OK
    expired_since = get_state(SATU).get("expired_since")
    login_at = load_cookies(SATU_SESSION_FILE).get("login_at")
    # Sesi yang berakhir tidak dicoba lagi, kecuali ada login baru (mis. disalin dari laptop).
    if expired_since and not (
        login_at and datetime.fromisoformat(login_at) > datetime.fromisoformat(expired_since)
    ):
        log.info("[-] SATU: sesi berakhir sejak %s, menunggu login ulang", expired_since)
        return EXIT_LOGIN_REQUIRED

    http = cookie_session(SATU_SESSION_FILE)
    try:
        session = silent_relogin(http)
    except LoginRequired as e:
        log.error("[x] SATU: %s setelah bertahan %s sejak login.", e, _session_age())
        report_login_expired(SATU, "keepalive")
        return EXIT_LOGIN_REQUIRED
    except (requests.RequestException, ValueError) as e:
        log.warning("[!] SATU: keep-alive gagal, bukan karena sesi: %s", e)
        return EXIT_ERROR

    persist_cookie_updates(SATU_SESSION_FILE, http)
    report_login_ok(SATU)
    log.info(
        "[ok] SATU: sesi aktif (umur %s, token berlaku sampai %s)",
        _session_age(),
        _token_expiry(session.get("accessToken")) or "?",
    )
    return EXIT_OK


def run() -> int:
    return max(keep_moodle_alive(), keep_satu_alive())
