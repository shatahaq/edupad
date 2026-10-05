"""Jadwal kuliah & presensi dari portal SATU USU (satu.usu.ac.id/mahasiswa).

Portal SATU memakai SSO Keycloak (id.usu.ac.id) yang terpisah dari SSO
kelas.usu.ac.id. Sesi Keycloak berakhir setelah beberapa jam tidak dipakai
(cookie aplikasinya bertahan 30 hari, tapi token di dalamnya tidak). Jadwal
jarang berubah, jadi data terakhir tetap dipakai dan login ulang cukup saat
KRS berubah. Data diambil dari API JSON yang dipakai halaman portal itu sendiri.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime

import requests

from edupad.config import (
    REQUEST_TIMEOUT,
    SATU_LOCK_FILE,
    SATU_PROFILE_DIR,
    SATU_SESSION_FILE,
    SATU_URL,
    SCHEDULE_DIR,
    WIB,
)
from edupad.core.academic import SCHEDULE_FILE
from edupad.core.files import now_iso, write_json, write_text_atomic
from edupad.core.lock import AlreadyRunning, wait_for_lock
from edupad.core.session import (
    SATU,
    cookie_session,
    load_cookies,
    persist_cookie_updates,
    report_login_expired,
    report_login_ok,
    save_cookies,
)
from edupad.errors import EXIT_ERROR, EXIT_LOGIN_REQUIRED, EXIT_OK, LoginRequired

log = logging.getLogger(__name__)

SUMMARY_FILE = SCHEDULE_DIR / "summary.md"
DAYS = ["senin", "selasa", "rabu", "kamis", "jumat", "sabtu", "minggu"]
LOGIN_TIMEOUT_MS = 5 * 60_000


def login_with_browser() -> None:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(str(SATU_PROFILE_DIR), headless=False)
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(f"{SATU_URL}/home", wait_until="domcontentloaded")
        log.info('[..] Login portal SATU di jendela browser (centang "Ingat saya"), maks. 5 menit.')
        try:
            page.wait_for_url(lambda u: u.startswith(SATU_URL) and "/auth/" not in u,
                              timeout=LOGIN_TIMEOUT_MS)
        except PlaywrightTimeoutError:
            raise LoginRequired("login portal SATU tidak selesai") from None
        page.wait_for_load_state("networkidle")
        # login_at ikut disimpan agar umur sesi terukur walau file disalin ke server
        save_cookies(SATU_SESSION_FILE, context.cookies(), page.evaluate("navigator.userAgent"),
                     login_at=now_iso())
        context.close()
    log.info("[ok] Sesi SATU tersimpan di %s", SATU_SESSION_FILE)


def satu_session(http: requests.Session) -> dict:
    """Isi /app/auth/session. Memanggilnya membuat portal memperbarui token Keycloak."""
    session = get_json(http, "/app/auth/session")
    if session.get("error"):  # mis. KeycloakSessionEnded: token tidak bisa diperbarui lagi
        raise LoginRequired(f"sesi SATU berakhir ({session['error']})")
    if not (session.get("user") or {}).get("identity"):
        raise LoginRequired("sesi SATU sudah habis")
    return session


def silent_relogin(http: requests.Session) -> dict:
    """Login ulang portal SATU memakai cookie SSO Keycloak, seperti yang dilakukan browser.

    Keycloak memutus sesi yang menganggur ~30 menit, dan /app/auth/session saja tidak
    menyentuh Keycloak selama access token portal masih berlaku. Alur signin ini
    melewati Keycloak sehingga batas menganggurnya ter-reset, tanpa password.
    """
    csrf = get_json(http, "/app/auth/csrf")["csrfToken"]
    r = http.post(f"{SATU_URL}/app/auth/signin/keycloak", timeout=REQUEST_TIMEOUT, allow_redirects=False,
                  data={"csrfToken": csrf, "callbackUrl": f"{SATU_URL}/home", "json": "true"})
    auth_url = (r.json().get("url") if "json" in r.headers.get("content-type", "")
                else r.headers.get("location"))
    if not auth_url or "/protocol/openid-connect/auth" not in auth_url:
        raise ValueError(f"alur signin portal SATU tidak dikenali (HTTP {r.status_code})")
    r = http.get(auth_url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
    if r.url.startswith("https://id.usu.ac.id"):  # berhenti di form login = SSO Keycloak habis
        raise LoginRequired("sesi SSO Keycloak berakhir")
    return satu_session(http)


def get_json(http: requests.Session, path: str, token: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    r = http.get(f"{SATU_URL}{path}", headers=headers, timeout=REQUEST_TIMEOUT, allow_redirects=False)
    time.sleep(1)
    if r.status_code in (301, 302, 303, 307, 401, 403):
        raise LoginRequired(f"HTTP {r.status_code} dari {path}")
    r.raise_for_status()
    return r.json()


def simplify_class(c: dict) -> dict:
    code = c.get("course_code") or ""
    return {
        "hari": c.get("day"),
        "mulai": c.get("start_time"),
        "selesai": c.get("end_time"),
        "kode": code,
        "matkul": c.get("course_name"),
        "jenis": "praktikum" if code.strip().endswith(" P") else "teori",
        "kelas": c.get("class_name"),
        "sks": c.get("credits"),
        "ruang": c.get("room_code"),
        "nama_ruang": c.get("room_name"),
        "gedung": c.get("building_location"),
        "dosen": [d["full_name"] for d in c.get("lecturers") or [] if d.get("full_name")],
        "moodle_course_id": c.get("elearning_class_id"),
        "satu_class_id": c.get("class_id"),
    }


def simplify_presence(p: dict) -> dict:
    first = (p.get("presence") or [{}])[0]
    return {
        "kode": p.get("course_code"),
        "matkul": p.get("course_name"),
        "kelas": p.get("class_name"),
        "satu_class_id": p.get("class_id"),
        "pertemuan_tercatat": first.get("presence_total"),
        "hadir": first.get("attendance"),
        "persen_hadir": round((first.get("percentage") or 0) * 100),
    }


def fetch_schedule(http: requests.Session) -> dict:
    session = satu_session(http)
    nim = session["user"]["identity"]
    token = session.get("accessToken")

    schedule = get_json(http, f"/app/proxy/study-card/schedule/nim/{nim}", token)
    classes = [simplify_class(c) for group in schedule.get("data") or [] for c in group.get("data") or []]
    order = {day: i for i, day in enumerate(DAYS)}
    classes.sort(key=lambda k: (order.get(k["hari"], 99), k["mulai"] or "99"))

    presence = []
    try:
        data = get_json(http, f"/app/proxy/study-card/course-class/presence/{nim}", token)
        presence = [simplify_presence(p) for p in data.get("data") or []]
    except (requests.RequestException, ValueError) as e:
        log.warning("[!] presensi gagal diambil: %s", e)

    return {
        "diperbarui": datetime.now(WIB).isoformat(timespec="minutes"),
        "sesi_berlaku_sampai": session.get("expires"),
        "nim": nim,
        "kelas": classes,
        "presensi": presence,
    }


def write_summary(result: dict) -> None:
    lines = ["# Jadwal Kuliah", "", f"Diperbarui: {result['diperbarui']} (WIB)", ""]
    for day in DAYS:
        rows = [k for k in result["kelas"] if k["hari"] == day and k["mulai"]]
        if not rows:
            continue
        lines += [f"## {day.capitalize()}", "", "| Jam | Mata kuliah | Kelas | Ruang | Dosen |",
                  "|---|---|---|---|---|"]
        lines += [f"| {k['mulai']}–{k['selesai']} | {k['matkul']} ({k['kode']}) | {k['kelas']} "
                  f"| {k['ruang']} | {', '.join(k['dosen'])} |" for k in rows]
        lines.append("")
    unscheduled = [k for k in result["kelas"] if not k["hari"] or not k["mulai"]]
    if unscheduled:
        lines += ["## Tanpa jadwal tetap", ""]
        lines += [f"- {k['matkul']} ({k['kode']})" for k in unscheduled] + [""]
    lines += ["## Presensi", "", "| Mata kuliah | Hadir | Persen |", "|---|---|---|"]
    lines += [f"| {p['matkul']} ({p['kelas']}) | {p['hadir']}/{p['pertemuan_tercatat']} "
              f"| {p['persen_hadir']}% |" for p in result["presensi"]]
    write_text_atomic(SUMMARY_FILE, "\n".join(lines) + "\n")


def run(login: bool = False) -> int:
    SCHEDULE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with wait_for_lock(SATU_LOCK_FILE):
            return _run(login)
    except AlreadyRunning as e:
        log.warning("[!] %s terlalu lama, jadwal tidak diperbarui", e)
        return EXIT_ERROR


def _run(login: bool) -> int:
    try:
        if login:
            login_with_browser()
        if not load_cookies(SATU_SESSION_FILE).get("cookies"):
            raise LoginRequired("belum ada sesi SATU tersimpan")
        http = cookie_session(SATU_SESSION_FILE)
        result = fetch_schedule(http)
        persist_cookie_updates(SATU_SESSION_FILE, http)
    except LoginRequired as e:
        log.error("[x] %s. Jadwal terakhir tetap dipakai; login ulang saat KRS berubah: "
                  "python -m edupad schedule --login", e)
        report_login_expired(SATU, "pengambil jadwal")
        return EXIT_LOGIN_REQUIRED
    except requests.RequestException as e:
        log.warning("[!] Portal SATU tidak bisa dihubungi: %s (jadwal lama tetap dipakai)", e)
        return EXIT_ERROR
    report_login_ok(SATU)

    write_json(SCHEDULE_FILE, result)
    write_summary(result)
    log.info("[selesai] %d kelas, %d data presensi. Sesi SATU berlaku sampai %s",
             len(result["kelas"]), len(result["presensi"]), result["sesi_berlaku_sampai"])
    return EXIT_OK
