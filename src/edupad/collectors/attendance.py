"""Presensi kelas dari portal SATU: notifikasi dan isi presensi mandiri otomatis.

Satu pertemuan dianggap perlu diisi bila status presensinya masih kosong dan
presensi sedang dibuka (flag `active`, atau waktu sekarang di antara jam mulai
dan jam akhir pertemuan). Tiap pertemuan hanya dinotifikasi sekali.

Pengisian otomatis (`--fill`) meniru form presensi di halaman class/[classId] portal
(POST multipart ke /study-card/presence). Hasilnya selalu dicek ulang dengan membaca
presensi lagi, karena server bisa menolak, mis. karena lokasi.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

import requests

from edupad.collectors.schedule import get_json, satu_session, with_relogin
from edupad.config import (
    LOG_DIR,
    REQUEST_TIMEOUT,
    SATU_LOCK_FILE,
    SATU_SESSION_FILE,
    SATU_URL,
    SCHEDULE_DIR,
    USU_LATITUDE,
    USU_LOCATION,
    USU_LONGITUDE,
    WIB,
)
from edupad.core.academic import krs_classes
from edupad.core.files import now_iso, write_json
from edupad.core.lock import AlreadyRunning, wait_for_lock
from edupad.core.notify import notify
from edupad.core.session import (
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

ATTENDANCE_FILE = SCHEDULE_DIR / "attendance.json"
MAX_REMEMBERED = 300  # id pertemuan yang sudah dinotifikasi
DIRECT_PRESENCE_PATH = "/app/proxy/study-card/presence"
FILL_FAILURE_LOG = LOG_DIR / "attendance_fill_failures.jsonl"

FILLED, ERROR, QR_ONLY, DRY_RUN = "filled", "error", "skip_qr_only", "dry_run"


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=WIB)
    except ValueError:
        return None


def simplify_meeting(meeting: dict, now: datetime) -> dict:
    start, end = (
        _parse_time(meeting.get("meeting_date")),
        _parse_time(meeting.get("meeting_end_time")),
    )
    is_open = bool(meeting.get("active")) or bool(start and end and start <= now <= end)
    status = meeting.get("presence")
    return {
        "id": meeting.get("id"),
        "pertemuan": meeting.get("meeting_count"),
        "nama": meeting.get("meeting_name"),
        "mulai": start.isoformat(timespec="minutes") if start else None,
        "selesai": end.isoformat(timespec="minutes") if end else None,
        "topik": meeting.get("realized_learning_material"),
        "status": status,
        "dibuka": is_open,
        "perlu_diisi": status is None and is_open,
        "cara": [
            m
            for m, flag in (("QR", meeting.get("use_qr")), ("langsung", meeting.get("use_direct")))
            if flag
        ],
    }


def fetch_attendance(http: requests.Session, session: dict | None = None) -> list[dict]:
    session = session or satu_session(http)
    nim, token = session["user"]["identity"], session.get("accessToken")
    now = datetime.now(WIB)
    courses = []
    for k in krs_classes():
        data = get_json(http, f"/app/proxy/study-card/presence/{k['satu_class_id']}/{nim}", token)[
            "data"
        ]
        meetings = [
            simplify_meeting(m, now)
            for group in data.get("presences") or []
            for m in group.get("class_meeting") or []
        ]
        meetings.sort(key=lambda m: m["pertemuan"] or 0)
        courses.append(
            {
                "matkul": k["matkul"],
                "kode": k["kode"],
                "kelas": k["kelas"],
                "moodle_course_id": k["moodle_course_id"],
                "satu_class_id": k["satu_class_id"],
                "pertemuan": meetings,
            }
        )
    return courses


def post_form(http: requests.Session, path: str, token: str | None, fields: dict) -> dict:
    """POST multipart seperti FormData di browser; semua nilai dikirim sebagai string."""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    files = {k: (None, str(v)) for k, v in fields.items()}
    r = http.post(
        f"{SATU_URL}{path}",
        headers=headers,
        files=files,
        timeout=REQUEST_TIMEOUT,
        allow_redirects=False,
    )
    if r.status_code in (301, 302, 303, 307, 401):
        raise LoginRequired(f"HTTP {r.status_code} dari POST {path}")
    # isi respons ikut dicatat: alasan penolakan (mis. lokasi) ada di sana
    if r.status_code >= 400:
        raise requests.HTTPError(
            f"HTTP {r.status_code} dari POST {path}: {r.text[:300]}", response=r
        )
    try:
        return r.json()
    except ValueError:
        raise ValueError(
            f"respons POST {path} bukan JSON (HTTP {r.status_code}): {r.text[:300]}"
        ) from None


def fill_one(
    http: requests.Session,
    session: dict,
    class_id: str,
    meeting_id: str,
    lat: float = USU_LATITUDE,
    lon: float = USU_LONGITUDE,
    location: str = USU_LOCATION,
) -> dict:
    return post_form(
        http,
        DIRECT_PRESENCE_PATH,
        session.get("accessToken"),
        {
            "class_meeting_id": meeting_id,
            "class_id": class_id,
            "latitude": lat,
            "longitude": lon,
            "location": location,
            "nim": session["user"]["identity"],
        },
    )


def fill_attendance(
    http: requests.Session,
    session: dict,
    courses: list[dict],
    lat: float = USU_LATITUDE,
    lon: float = USU_LONGITUDE,
    dry_run: bool = False,
) -> list[dict]:
    """Isi presensi yang terbuka dan mendukung cara "langsung"; QR harus dipindai sendiri."""
    results = []
    for course in courses:
        for meeting in course["pertemuan"]:
            if not meeting["perlu_diisi"]:
                continue
            result = {
                "id": meeting["id"],
                "kode": course["kode"],
                "matkul": course["matkul"],
                "kelas": course["kelas"],
                "pertemuan": meeting["nama"],
            }
            results.append(result)
            if "langsung" not in meeting["cara"]:
                result["status"] = QR_ONLY
                log.info("[skip] %s %s: hanya QR", course["kode"], meeting["nama"])
            elif dry_run:
                result["status"] = DRY_RUN
                log.info(
                    "[dry-run] %s %s: akan diisi (%.4f, %.4f)",
                    course["kode"],
                    meeting["nama"],
                    lat,
                    lon,
                )
            else:
                try:
                    result["response"] = fill_one(
                        http, session, course["satu_class_id"], meeting["id"], lat, lon
                    )
                    result["status"] = FILLED
                except (requests.RequestException, ValueError, LoginRequired) as e:
                    result.update(status=ERROR, error=str(e))
                    log.warning("[!] %s %s: gagal mengisi: %s", course["kode"], meeting["nama"], e)
    return results


def verify_filled(results: list[dict], courses: list[dict]) -> None:
    """Server bisa membalas 200 tanpa mencatat presensi; percayai status terbaru saja."""
    status = {m["id"]: m["status"] for c in courses for m in c["pertemuan"]}
    for r in results:
        if r["status"] != FILLED:
            continue
        if status.get(r["id"]) is None:
            r.update(
                status=ERROR, error="server menerima permintaan, tapi status presensi masih kosong"
            )
            log.warning(
                "[!] %s %s: %s (respons: %s)", r["kode"], r["pertemuan"], r["error"], r["response"]
            )
        else:
            log.info("[ok] %s %s: presensi terisi (%s)", r["kode"], r["pertemuan"], status[r["id"]])


def log_fill_failures(results: list[dict]) -> None:
    """Catat tiap percobaan gagal ke JSONL agar bisa ditelusuri setelah kelas selesai."""
    failures = [r for r in results if r["status"] in (ERROR, QR_ONLY)]
    if not failures:
        return
    FILL_FAILURE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with FILL_FAILURE_LOG.open("a", encoding="utf-8") as f:
        for r in failures:
            entry = {"waktu": now_iso(), **r}
            if r["status"] == QR_ONLY:
                entry["error"] = "hanya bisa lewat QR"
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
    log.warning(
        "[!] %d presensi gagal diisi otomatis, detail di %s", len(failures), FILL_FAILURE_LOG
    )


def _message(course: dict, meeting: dict, error: str | None = None) -> str:
    end = (
        datetime.fromisoformat(meeting["selesai"]).strftime("%H:%M") if meeting["selesai"] else None
    )
    lines = [f"📝 Presensi dibuka: {course['matkul']} ({course['kelas']}) — {meeting['nama']}"]
    if meeting["topik"]:
        lines.append(f"Topik: {meeting['topik']}")
    if end:
        lines.append(f"Isi sebelum {end} WIB.")
    if meeting["cara"]:
        lines.append(
            f"Cara: {' / '.join(meeting['cara'])} (menu Presensi Kelas di {SATU_URL.split('//')[1]})"
        )
    if error:
        lines.append(f"⚠️ Gagal diisi otomatis: {error}")
    return "\n".join(lines)


def _filled_message(result: dict) -> str:
    return f"✅ Presensi terisi otomatis: {result['matkul']} ({result['kelas']}) — {result['pertemuan']}"


def send_notifications(courses: list[dict], results: list[dict]) -> None:
    """Satu pesan per pertemuan: dibuka (plus alasan gagal bila ada) atau berhasil diisi."""
    by_id = {r["id"]: r for r in results}
    for r in results:
        if r["status"] == FILLED:
            notify(_filled_message(r))

    notified = list(get_state(SATU).get("attendance_notified", []))
    for course in courses:
        for meeting in course["pertemuan"]:
            result = by_id.get(meeting["id"], {})
            if (
                not meeting["perlu_diisi"]
                or result.get("status") == FILLED
                or meeting["id"] in notified
            ):
                continue
            if notify(_message(course, meeting, result.get("error"))):
                notified.append(meeting["id"])
            log.info("[notif] %s %s", course["kode"], meeting["nama"])
    update_state(SATU, attendance_notified=notified[-MAX_REMEMBERED:])


def run(fill: bool = False, dry_run: bool = False) -> int:
    try:
        with wait_for_lock(SATU_LOCK_FILE):
            return _run(fill, dry_run)
    except AlreadyRunning as e:
        log.warning("[!] %s terlalu lama, pengecekan presensi dilewati", e)
        return EXIT_ERROR


def _run(fill: bool, dry_run: bool) -> int:
    if not load_cookies(SATU_SESSION_FILE).get("cookies"):
        log.error("[x] Belum ada sesi SATU. Login: python -m edupad schedule --login")
        return EXIT_LOGIN_REQUIRED
    if not krs_classes():
        log.error("[x] Jadwal (KRS) belum ada. Jalankan: python -m edupad schedule")
        return EXIT_ERROR

    http = cookie_session(SATU_SESSION_FILE)

    def check(session: dict) -> tuple[list[dict], list[dict]]:
        courses = fetch_attendance(http, session)
        results: list[dict] = []
        if fill:
            results = fill_attendance(http, session, courses, dry_run=dry_run)
            if any(r["status"] == FILLED for r in results):
                courses = fetch_attendance(http, session)
                verify_filled(results, courses)
        return courses, results

    try:
        courses, results = with_relogin(http, check)
    except LoginRequired as e:
        log.error("[x] %s. Presensi tidak bisa dipantau sampai login ulang.", e)
        report_login_expired(SATU, "pemantau presensi")
        return EXIT_LOGIN_REQUIRED
    except (requests.RequestException, ValueError, KeyError) as e:
        log.warning("[!] Portal SATU tidak bisa dibaca: %s", e)
        return EXIT_ERROR
    persist_cookie_updates(SATU_SESSION_FILE, http)
    report_login_ok(SATU)

    if not dry_run:
        log_fill_failures(results)
        send_notifications(courses, results)
    write_json(ATTENDANCE_FILE, {"diperbarui": now_iso(), "mata_kuliah": courses})

    open_count = sum(m["perlu_diisi"] for c in courses for m in c["pertemuan"])
    log.info("[ok] %d kelas dicek, %d presensi perlu diisi.", len(courses), open_count)
    if fill:
        count = {
            s: sum(r["status"] == s for r in results) for s in (FILLED, ERROR, QR_ONLY, DRY_RUN)
        }
        log.info(
            "[fill] %d terisi, %d gagal, %d hanya QR, %d dry-run.",
            count[FILLED],
            count[ERROR],
            count[QR_ONLY],
            count[DRY_RUN],
        )
    return EXIT_OK
