"""Menjaga sesi login tetap aktif (dijalankan tiap ~20 menit).

- kelas.usu.ac.id: sesi Moodle kedaluwarsa bila menganggur > 8 jam;
  core_session_touch (dipakai halaman Moodle sendiri) memperpanjangnya. Bila sesi
  tetap terputus (mis. diakhiri server), login ulang otomatis lewat token SSO USU,
  paling sering sekali per SSO_RELOGIN_INTERVAL agar tidak memutus sesi di perangkat lain.
- Portal SATU: Keycloak (id.usu.ac.id) memutus sesi yang menganggur ~30 menit dan
  sesi portal punya batas keras ~8 jam, sedangkan cookie SSO-nya ("Ingat saya") berlaku
  ~30 hari. Tiap run melakukan login ulang senyap lewat cookie SSO: batas menganggur
  ter-reset dan sesi portal baru dibuat setelah batas 8 jam. Tetap dicoba walau sesi sudah
  ditandai berakhir, sehingga pulih sendiri selama cookie SSO masih berlaku.
"""

from __future__ import annotations

import base64
import json
import logging
from datetime import datetime, timedelta

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

SSO_RELOGIN_INTERVAL = timedelta(hours=2)


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


def _try_sso_relogin(client: MoodleClient) -> bool:
    last = get_state(MOODLE).get("last_sso_relogin")
    if last and datetime.now(WIB) - datetime.fromisoformat(last) < SSO_RELOGIN_INTERVAL:
        log.info(
            "[-] Moodle: login ulang SSO terakhir %s, menunggu jeda %s", last, SSO_RELOGIN_INTERVAL
        )
        return False
    update_state(MOODLE, last_sso_relogin=datetime.now(WIB).isoformat(timespec="seconds"))
    try:
        client.sso_relogin()
    except (LoginRequired, requests.RequestException) as e:
        log.error("[x] Moodle: login ulang lewat SSO gagal: %s", e)
        return False
    log.info("[ok] Moodle: sesi diperbarui lewat token SSO USU (tanpa password)")
    return True


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
            try:
                client.fetch_sesskey()  # sesskey cache basi setelah login ulang
            except LoginRequired:
                if not _try_sso_relogin(client):
                    raise
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
    sso = client.sso_token_expiry()
    log.info(
        "[ok] Moodle: sesi aktif. Sisa sebelum touch: %s, setelah: %s. Token SSO berlaku sampai %s",
        _format_duration(before),
        _format_duration(after),
        datetime.fromtimestamp(sso, WIB).strftime("%d-%m %H:%M WIB") if sso else "-",
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
    # Sesi yang ditandai berakhir tetap dicoba: tanda itu bisa berasal dari job lain yang
    # kebetulan menemui batas ~8 jam sesi portal, padahal cookie SSO masih bisa dipakai.
    expired_since = get_state(SATU).get("expired_since")
    http = cookie_session(SATU_SESSION_FILE)
    try:
        session = silent_relogin(http)
    except LoginRequired as e:
        if expired_since:
            log.info("[-] SATU: %s; masih perlu login ulang (sejak %s)", e, expired_since)
        else:
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
