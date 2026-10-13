"""Google Classroom -> data untuk AI agent (padanan assignments.py untuk kelas.usu.ac.id).

Untuk setiap akun Google yang login di web EduPad dan memberi izin Classroom: kelas aktif
sebagai siswa, topik, tugas + status pengumpulan milik sendiri, materi, dan pengumuman.
Hasil per akun di data/classroom/<sub>.json. Hanya membaca; tidak ada yang dikirim ke
Classroom. Izin yang tidak diberikan (granular consent) dilewati tanpa menggagalkan sinkronisasi.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from datetime import datetime, timezone

import requests

from edupad.config import CLASSROOM_DIR, WIB, get_settings
from edupad.core import http_pool
from edupad.core.academic import meeting_number
from edupad.core.files import write_json
from edupad.core.lock import AlreadyRunning, acquire_lock, release_lock
from edupad.errors import EXIT_ERROR, EXIT_LOGIN_REQUIRED, EXIT_OK
from edupad.google import oauth
from edupad.google.accounts import AccountStore, edupad_user_id, has_classroom

log = logging.getLogger(__name__)

API_URL = "https://classroom.googleapis.com/v1"
TIMEOUT = 30
PAGE_SIZE = 100
MAX_PAGES = 50  # pengaman bila API terus mengirim nextPageToken
MAX_ANNOUNCEMENTS = 50  # pengumuman terbaru per kelas
SOURCE = "Google Classroom"
DONE_STATES = {"TURNED_IN", "RETURNED"}
WORK_TYPES = {
    "ASSIGNMENT": "tugas",
    "SHORT_ANSWER_QUESTION": "pertanyaan",
    "MULTIPLE_CHOICE_QUESTION": "pertanyaan",
}


class ClassroomError(RuntimeError):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


# --------------------------------- API ---------------------------------------
def _get(token: str, path: str, params: dict) -> dict:
    try:
        response = http_pool.get(
            f"{API_URL}{path}",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
            timeout=TIMEOUT,
        )
    except requests.RequestException as e:
        raise ClassroomError(f"Classroom tidak bisa dihubungi: {e}") from e
    if not response.ok:
        try:
            message = response.json().get("error", {}).get("message") or response.text[:200]
        except (ValueError, AttributeError):
            message = response.text[:200]
        raise ClassroomError(
            f"Classroom HTTP {response.status_code} {path}: {message}", response.status_code
        )
    try:
        body = response.json()
    except ValueError as e:
        raise ClassroomError(f"jawaban Classroom bukan JSON: {path}") from e
    return body if isinstance(body, dict) else {}


def paged(token: str, path: str, key: str, params: dict, limit: int | None = None) -> list[dict]:
    """Semua item dari endpoint list Classroom (`key` = nama field array di respons)."""
    items: list[dict] = []
    page_token = None
    for _ in range(MAX_PAGES):
        query = {
            **params,
            "pageSize": PAGE_SIZE,
            **({"pageToken": page_token} if page_token else {}),
        }
        body = _get(token, path, query)
        items += body.get(key) or []
        page_token = body.get("nextPageToken")
        if not page_token or (limit and len(items) >= limit):
            break
    return items[:limit] if limit else items


# ------------------------------ normalisasi ----------------------------------
def to_wib(timestamp: str | None) -> str | None:
    """RFC 3339 dari Classroom ('2026-10-01T03:04:05.123Z') -> '2026-10-01T10:04+07:00'."""
    if not timestamp:
        return None
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(WIB).isoformat(timespec="minutes")


def due(work: dict) -> tuple[str | None, int | None]:
    """Deadline (ISO WIB, epoch) dari dueDate + dueTime (UTC).

    JSON proto3 menghilangkan angka 0, jadi jam 00:00 UTC datang sebagai dueTime {}.
    """
    date = work.get("dueDate")
    if not date:
        return None, None
    time_of_day = work.get("dueTime") or {}
    try:
        moment = datetime(
            int(date["year"]),
            int(date["month"]),
            int(date["day"]),
            int(time_of_day.get("hours", 0)),
            int(time_of_day.get("minutes", 0)),
            int(time_of_day.get("seconds", 0)),
            tzinfo=timezone.utc,
        )
    except (KeyError, TypeError, ValueError):
        return None, None
    return moment.astimezone(WIB).isoformat(timespec="minutes"), int(moment.timestamp())


def attachments(materials: list[dict] | None) -> list[dict]:
    """Lampiran Classroom (Drive, YouTube, tautan, Form, Gem, NotebookLM) -> {jenis, judul, url}."""
    out = []
    for material in materials or []:
        if "driveFile" in material:
            item = (material.get("driveFile") or {}).get("driveFile") or {}
            out.append(
                {
                    "jenis": "drive",
                    "judul": item.get("title"),
                    "url": item.get("alternateLink"),
                    "drive_id": item.get("id"),
                }
            )
        elif "youtubeVideo" in material:
            item = material.get("youtubeVideo") or {}
            out.append(
                {"jenis": "youtube", "judul": item.get("title"), "url": item.get("alternateLink")}
            )
        elif "link" in material:
            item = material.get("link") or {}
            out.append(
                {
                    "jenis": "tautan",
                    "judul": item.get("title") or item.get("url"),
                    "url": item.get("url"),
                }
            )
        elif "form" in material:
            item = material.get("form") or {}
            out.append({"jenis": "form", "judul": item.get("title"), "url": item.get("formUrl")})
        else:
            for kind in ("gem", "notebook"):
                if kind in material:
                    item = material.get(kind) or {}
                    out.append({"jenis": kind, "judul": item.get("title"), "url": item.get("url")})
    return out


def _number(value: float | None) -> str:
    return f"{value:g}" if isinstance(value, (int, float)) else "-"


def meeting_of(topic: str | None, title: str) -> int | None:
    """Nomor pertemuan dari nama topik ('Pertemuan 3', '03 - Basis Data'), atau dari judul
    yang menyebut 'pertemuan N'. Judul seperti '2 Soal Latihan' tidak dianggap pertemuan."""
    if topic:
        number = meeting_number(topic, None)
        if number:
            return number
    match = re.search(r"pertemuan\s*(\d+)", title or "", re.I)
    return int(match.group(1)) if match else None


def task_status(work: dict, submission: dict | None, now_ts: int) -> dict:
    """Status pengumpulan dengan bentuk yang sama seperti tugas kelas.usu.ac.id."""
    state = (submission or {}).get("state")
    late = bool((submission or {}).get("late"))
    grade = (submission or {}).get("assignedGrade")
    if state == "TURNED_IN":
        text = "Sudah dikumpulkan" + (" (terlambat)" if late else "")
    elif state == "RETURNED":
        text = "Sudah dikembalikan guru"
        if grade is not None:
            text += f", nilai: {_number(grade)}/{_number(work.get('maxPoints'))}"
    elif state == "RECLAIMED_BY_STUDENT":
        text = "Ditarik kembali, BELUM dikumpulkan"
    elif state in {"NEW", "CREATED"}:
        text = "BELUM dikumpulkan"
    else:
        text = "Status tidak diketahui"
    done = state in DONE_STATES
    _, due_ts = due(work)
    overdue = bool(due_ts and due_ts < now_ts)
    if not done and overdue:
        text += " — LEWAT DEADLINE"
    return {
        "status": {"state": state, "terlambat": late, "nilai": grade},
        "sudah_dikumpulkan": done,
        "lewat_deadline": overdue,
        "status_ringkas": text,
    }


def course_entry(course: dict) -> dict:
    name = (course.get("name") or "").strip()
    section = (course.get("section") or "").strip()
    aliases = {name.lower(), f"{name} {section}".strip().lower()}
    return {
        "course_id": f"gc-{course['id']}",
        "id": course["id"],
        "nama": name,
        "bagian": section or None,
        "ruang": course.get("room") or None,
        "deskripsi": course.get("descriptionHeading") or course.get("description") or None,
        "url": course.get("alternateLink"),
        "alias": sorted(a for a in aliases if a),
    }


def task_entry(
    course: dict, work: dict, submission: dict | None, topic: str | None, now_ts: int
) -> dict:
    deadline, deadline_ts = due(work)
    return {
        "sumber": SOURCE,
        "course_id": course["course_id"],
        "matkul": course["nama"],
        "jenis": WORK_TYPES.get(work.get("workType"), "tugas"),
        "judul": work.get("title") or "(tanpa judul)",
        "topik": topic,
        "pertemuan": meeting_of(topic, work.get("title") or ""),
        "url": work.get("alternateLink"),
        "deskripsi": work.get("description") or "",
        "deadline": deadline,
        "deadline_ts": deadline_ts,
        "poin_maks": work.get("maxPoints"),
        "lampiran": attachments(work.get("materials")),
        "dibuat": to_wib(work.get("creationTime")),
        "diperbarui": to_wib(work.get("updateTime")),
        **task_status(work, submission, now_ts),
    }


def material_entry(course: dict, item: dict, kind: str, topic: str | None) -> dict:
    if kind == "pengumuman":
        text = item.get("text") or ""
        first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
        title = first_line[:80] or "(pengumuman)"
        description = text
    else:
        title = item.get("title") or "(tanpa judul)"
        description = item.get("description") or ""
    return {
        "sumber": SOURCE,
        "course_id": course["course_id"],
        "matkul": course["nama"],
        "jenis": kind,
        "judul": title,
        "deskripsi": description,
        "topik": topic,
        "pertemuan": meeting_of(topic, title),
        "lampiran": attachments(item.get("materials")),
        "url": item.get("alternateLink"),
        "dibuat": to_wib(item.get("creationTime")),
        "diperbarui": to_wib(item.get("updateTime")),
    }


# ------------------------------- sinkronisasi --------------------------------
def fetch_course(
    token: str, scopes: set[str], course: dict, now_ts: int
) -> tuple[list, list, list]:
    """(tugas, materi, catatan error) satu kelas. Endpoint yang ditolak dicatat, tidak fatal."""
    entry = course_entry(course)
    base = f"/courses/{course['id']}"
    errors: list[str] = []

    def fetch(scope: str, name: str, call: Callable[[], list[dict]]) -> list[dict]:
        if not oauth.scope_granted(scopes, scope):
            return []  # izin ini tidak diberikan pengguna
        try:
            return call()
        except ClassroomError as e:
            if e.status in (403, 404):  # mis. fitur dimatikan admin sekolah, kelas dihapus
                errors.append(f"{entry['nama']}: {name}: {e}")
                return []
            raise

    topics = {
        t["topicId"]: t.get("name")
        for t in fetch(
            oauth.CLASSROOM_TOPICS, "topik", lambda: paged(token, f"{base}/topics", "topic", {})
        )
        if t.get("topicId")
    }
    works = fetch(
        oauth.CLASSROOM_COURSEWORK,
        "tugas",
        lambda: paged(token, f"{base}/courseWork", "courseWork", {}),  # bawaan: PUBLISHED
    )
    submissions = {
        s.get("courseWorkId"): s
        for s in fetch(
            oauth.CLASSROOM_COURSEWORK,
            "pengumpulan",
            lambda: paged(
                token,
                f"{base}/courseWork/-/studentSubmissions",
                "studentSubmissions",
                {"userId": "me"},
            ),
        )
    }
    materials = fetch(
        oauth.CLASSROOM_MATERIALS,
        "materi",
        lambda: paged(token, f"{base}/courseWorkMaterials", "courseWorkMaterial", {}),
    )
    announcements = fetch(
        oauth.CLASSROOM_ANNOUNCEMENTS,
        "pengumuman",
        lambda: paged(
            token,
            f"{base}/announcements",
            "announcements",
            {},  # bawaan: PUBLISHED, terbaru dulu
            limit=MAX_ANNOUNCEMENTS,
        ),
    )
    tasks = [
        task_entry(entry, w, submissions.get(w.get("id")), topics.get(w.get("topicId")), now_ts)
        for w in works
    ]
    items = [material_entry(entry, m, "materi", topics.get(m.get("topicId"))) for m in materials]
    items += [material_entry(entry, a, "pengumuman", None) for a in announcements]
    return tasks, items, errors


def sync_account(
    store: AccountStore,
    client: oauth.Client,
    account: dict,
    now: Callable[[], datetime] | None = None,
) -> dict:
    """Ambil seluruh data Classroom satu akun dan tulis ke data/classroom/<sub>.json."""
    moment = (now or (lambda: datetime.now(WIB)))()
    token = store.access_token(account["sub"], client)
    scopes = set(
        (store.get(account["sub"]) or account).get("scopes", [])
    )  # bisa berubah saat refresh
    courses = paged(token, "/courses", "courses", {"studentId": "me", "courseStates": "ACTIVE"})
    data: dict = {
        "diperbarui": moment.isoformat(timespec="minutes"),
        "sumber": SOURCE,
        "email": account["email"],
        "user_id": edupad_user_id(account["email"], account["sub"], get_settings()),
        "kelas": [course_entry(c) for c in courses],
        "tugas": [],
        "materi": [],
        "error": [],
    }
    for course in courses:
        tasks, items, errors = fetch_course(token, scopes, course, int(moment.timestamp()))
        data["tugas"] += tasks
        data["materi"] += items
        data["error"] += errors
    data["tugas"].sort(key=lambda t: (t["deadline_ts"] is None, t["deadline_ts"] or 0))
    data["materi"].sort(key=lambda m: m["dibuat"] or "", reverse=True)
    write_json(CLASSROOM_DIR / f"{account['sub']}.json", data, private=True)
    return data


def run(email: str | None = None) -> int:
    """Sinkronkan semua akun (atau satu email). Dipakai cron dan setelah login di web."""
    client = oauth.Client.from_settings(get_settings())
    if client is None:
        log.error("[x] GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET belum diisi di .env")
        return EXIT_ERROR
    store = AccountStore()
    accounts = [a for a in store.all() if email is None or a["email"].lower() == email.lower()]
    if not accounts:
        log.info("[-] belum ada akun Google yang login di web EduPad")
        return EXIT_OK
    code = EXIT_OK
    for account in accounts:
        if not has_classroom(account):
            log.info("[-] %s: izin Google Classroom belum diberikan", account["email"])
            continue
        lock_file = CLASSROOM_DIR / f".{account['sub']}.lock"
        try:
            fd = acquire_lock(lock_file)
        except AlreadyRunning:
            log.info("[-] %s: sinkronisasi lain sedang berjalan, dilewati", account["email"])
            continue
        try:
            data = sync_account(store, client, account)
        except oauth.ReauthRequired:
            log.error(
                "[x] %s: izin Google dicabut/kedaluwarsa, perlu login ulang di web",
                account["email"],
            )
            code = max(code, EXIT_LOGIN_REQUIRED)
            continue
        except (oauth.GoogleAuthError, ClassroomError) as e:
            log.error("[x] %s: %s", account["email"], e)
            code = max(code, EXIT_ERROR)
            continue
        finally:
            release_lock(fd)
        pending = sum(not t["sudah_dikumpulkan"] for t in data["tugas"])
        log.info(
            "[selesai] %s: %d kelas, %d tugas (%d belum dikumpulkan), %d materi & pengumuman",
            account["email"],
            len(data["kelas"]),
            len(data["tugas"]),
            pending,
            len(data["materi"]),
        )
        for error in data["error"]:
            log.warning("[!] %s", error)
    return code
