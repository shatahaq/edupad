"""Tugas (assign) & kuis (quiz): deadline, status pengumpulan, nilai, isi soal.

Tanpa browser. API mod_assign dimatikan di server USU, jadi status dibaca dari
halaman tugas; status diambil dari class CSS agar tidak bergantung bahasa tampilan.
Membuka halaman tugas tercatat di log Moodle sebagai "dilihat".
"""

from __future__ import annotations

import contextlib
import io
import json
import logging
import re
import time
from datetime import date, datetime
from html import unescape
from urllib.parse import parse_qs, unquote, urljoin, urlparse

from bs4 import BeautifulSoup

from edupad.config import ASSIGNMENTS_DIR, MOODLE_URL, WIB, get_settings
from edupad.core.academic import course_class, krs_course_ids, meeting_number
from edupad.core.files import read_json, safe_name, sha256_bytes, write_json, write_text_atomic
from edupad.core.markdown import html_to_markdown
from edupad.core.moodle import MoodleClient
from edupad.core.session import MOODLE, report_login_expired, report_login_ok
from edupad.errors import EXIT_ERROR, EXIT_LOGIN_REQUIRED, EXIT_OK, LoginRequired

log = logging.getLogger(__name__)

ASSIGNMENTS_FILE = ASSIGNMENTS_DIR / "assignments.json"
SUMMARY_FILE = ASSIGNMENTS_DIR / "summary.md"
ATTACHMENTS_DIR = ASSIGNMENTS_DIR / "attachments"
OCR_CACHE_FILE = ASSIGNMENTS_DIR / "ocr_cache.json"

MODULES = {"assign": "tugas", "quiz": "kuis"}
CALENDAR_MONTHS_BACK, CALENDAR_MONTHS_AHEAD = 5, 6
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")
MAX_ATTACHMENT_CHARS = 20_000
NO_DEADLINE = 2**40  # urutan: tugas tanpa deadline di paling bawah


def ts_to_iso(ts: int | None) -> str | None:
    return datetime.fromtimestamp(ts, WIB).isoformat(timespec="minutes") if ts else None


def parse_moodle_date(text: str) -> int | None:
    """'Tuesday, 15 September 2026, 11:30 AM' -> timestamp (cadangan bila tak ada di kalender)."""
    for fmt in ("%A, %d %B %Y, %I:%M %p", "%A, %d %B %Y, %H:%M"):
        try:
            return int(datetime.strptime(text.strip(), fmt).replace(tzinfo=WIB).timestamp())
        except ValueError:
            continue
    return None


class OcrCache:
    """Soal sering berupa gambar; OCR lambat, jadi hasilnya di-cache per isi gambar."""

    def __init__(self):
        self.data = read_json(OCR_CACHE_FILE)
        self._engine = None

    def text(self, image: bytes) -> str:
        key = sha256_bytes(image)
        if key not in self.data:
            if self._engine is None:
                with (
                    contextlib.redirect_stdout(io.StringIO()),
                    contextlib.redirect_stderr(io.StringIO()),
                ):
                    from rapidocr import RapidOCR

                    self._engine = RapidOCR()
                logging.getLogger("RapidOCR").setLevel(logging.WARNING)
            result = self._engine(image)
            self.data[key] = "\n".join(result.txts) if result.txts else ""
        return self.data[key]

    def save(self) -> None:
        write_json(OCR_CACHE_FILE, self.data)


# ------------------------------ Moodle data ----------------------------------
def select_courses(courses: list[dict]) -> list[dict]:
    """Hanya kelas milik mahasiswa: KRS bila ada, selain itu tebakan dari nama kelas."""
    settings = get_settings()
    krs = krs_course_ids()
    if krs:
        kept = [c for c in courses if c["id"] in krs and c["id"] not in settings.ignored_courses]
        reason = "tidak ada di KRS"
    else:
        kept = [
            c
            for c in courses
            if c["id"] not in settings.ignored_courses
            and (
                not settings.student_class
                or course_class(c["name"]) in (None, settings.student_class)
            )
        ]
        reason = f"bukan kelas {settings.student_class or 'saya'}"
    for c in courses:
        if c not in kept:
            log.info("[abaikan] %s (%s)", c["name"], reason)
    return kept


def course_tasks(client: MoodleClient, course: dict) -> list[dict]:
    state = json.loads(client.call("core_courseformat_get_state", {"courseid": int(course["id"])}))
    sections = {s["id"]: s for s in state.get("section", [])}
    tasks = []
    for cm in state.get("cm", []):
        if cm.get("module") not in MODULES or not cm.get("uservisible", True):
            continue
        sec = sections.get(cm.get("sectionid"), {})
        number = sec.get("number", cm.get("sectionnumber"))
        title = unescape(sec.get("title") or f"Section {number}")
        tasks.append(
            {
                "cmid": str(cm["id"]),
                "jenis": MODULES[cm["module"]],
                "module": cm["module"],
                "judul": unescape(cm["name"]),
                "course_id": course["id"],
                "matkul": course["name"],
                "section": title,
                "pertemuan": meeting_number(title, number),
                "url": cm.get("url") or f"{MOODLE_URL}/mod/{cm['module']}/view.php?id={cm['id']}",
            }
        )
    return tasks


def calendar_deadlines(client: MoodleClient) -> dict[str, dict[str, int]]:
    """cmid -> {eventtype: timestamp}, termasuk tugas yang sudah dikumpulkan."""
    out: dict[str, dict[str, int]] = {}
    today = date.today()
    for offset in range(-CALENDAR_MONTHS_BACK, CALENDAR_MONTHS_AHEAD + 1):
        year, month = divmod(today.year * 12 + today.month - 1 + offset, 12)
        data = client.call(
            "core_calendar_get_calendar_monthly_view",
            {"year": year, "month": month + 1, "courseid": 1, "day": 1, "mini": False},
        )
        for week in data["weeks"]:
            for day in week["days"]:
                for event in day["events"]:
                    if event.get("modulename") not in MODULES:
                        continue
                    cmid = parse_qs(urlparse(event.get("url", "")).query).get("id", [None])[0]
                    if cmid:
                        out.setdefault(cmid, {})[event.get("eventtype", "")] = event["timestart"]
        time.sleep(0.5)
    return out


# ------------------------------ page parsing ---------------------------------
def activity_dates(soup: BeautifulSoup) -> dict[str, str]:
    """{'Opened': 'Friday, 11 September 2026, 12:00 AM', 'Due': ...}"""
    box = soup.select_one("[data-region='activity-dates']")
    if not box:
        return {}
    dates = {}
    for div in box.find_all("div"):
        strong = div.find("strong")
        if strong and not div.find("div"):
            label = strong.get_text(strip=True)
            dates[label.rstrip(":")] = div.get_text(" ", strip=True).replace(label, "", 1).strip()
    return dates


def parse_assign(soup: BeautifulSoup) -> dict:
    rows, feedback, files = {}, {}, []
    submission = grading = timing = None
    for table in soup.select("table.generaltable"):
        in_feedback = table.find_parent(class_=re.compile(r"\bfeedback")) is not None
        for tr in table.select("tr"):
            th, td = tr.find("th"), tr.find("td")
            if not (th and td) or "___picture___" in td.get_text():  # template komentar kosong
                continue
            (feedback if in_feedback else rows)[th.get_text(" ", strip=True)] = td.get_text(
                " ", strip=True
            )
            files += [a.get_text(strip=True) for a in td.select("a[href*='assignsubmission_file']")]
            for cls in td.get("class", []):
                if cls.startswith("submissionstatus"):
                    submission = cls.removeprefix("submissionstatus")
                elif cls in ("submissiongraded", "submissionnotgraded"):
                    grading = cls
                elif cls in ("overdue", "earlysubmission", "latesubmission"):
                    timing = cls
    if rows and submission is None:
        submission = "new"  # "No submissions have been made yet" tidak ber-class
    grade = next((v for k, v in feedback.items() if k.lower() in ("grade", "nilai")), None)
    return {
        "pengumpulan": submission,
        "penilaian": {
            "submissiongraded": "sudah_dinilai",
            "submissionnotgraded": "belum_dinilai",
        }.get(grading),
        "waktu": {
            "overdue": "lewat_deadline",
            "earlysubmission": "tepat_waktu",
            "latesubmission": "terlambat",
        }.get(timing),
        "nilai": grade,
        "file_dikumpulkan": list(dict.fromkeys(files)),
        "detail": rows,
        "feedback": feedback,
    }


def parse_quiz(soup: BeautifulSoup) -> dict:
    info = soup.select_one(".quizinfo")
    attempts = []
    table = soup.select_one("table.quizattemptsummary")
    if table:
        headers = [th.get_text(" ", strip=True) for th in table.select("thead th")]
        for tr in table.select("tbody tr"):
            cells = [td.get_text(" ", strip=True) for td in tr.select("td")]
            attempts.append(
                dict(zip(headers, cells, strict=False))
            )  # baris ringkasan bisa lebih pendek
    grade = soup.select_one("#feedback")
    main = soup.select_one("div[role='main']")
    return {
        "info": info.get_text(" | ", strip=True) if info else None,
        "percobaan": attempts,
        "nilai": grade.get_text(" ", strip=True) if grade else None,
        "catatan": main.get_text(" | ", strip=True)[:500] if main else None,
    }


def save_attachment(client: MoodleClient, url: str, cmid: str) -> dict:
    from edupad.processing.convert import SUPPORTED_EXTS, convert_file  # impor berat, lazy

    name = safe_name(unquote(urlparse(url).path.rsplit("/", 1)[-1]))
    dest = ATTACHMENTS_DIR / cmid / name
    md_path = dest.with_name(dest.name + ".md")
    info = {"nama": name, "url": url, "path": dest.relative_to(ASSIGNMENTS_DIR).as_posix()}
    if dest.suffix.lower() in IMAGE_EXTS:
        return info
    try:
        r = client.http.get(url, timeout=60)
        time.sleep(1)
        r.raise_for_status()
        if not dest.exists() or dest.read_bytes() != r.content:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(r.content)
            if dest.suffix.lower() in SUPPORTED_EXTS:  # mis. .zip disimpan tanpa konversi
                md, _ = convert_file(dest)
                write_text_atomic(md_path, md)
        if md_path.exists():
            info["markdown"] = md_path.relative_to(ASSIGNMENTS_DIR).as_posix()
            info["isi"] = md_path.read_text(encoding="utf-8")[:MAX_ATTACHMENT_CHARS]
    except Exception as e:
        log.warning("      [lampiran gagal] %s: %s", name, e)
    return info


def task_description(
    soup: BeautifulSoup, client: MoodleClient, ocr: OcrCache, cmid: str
) -> tuple[str, list[dict]]:
    parts = []
    box = soup.select_one(".activity-description")
    if box:
        md = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", html_to_markdown(str(box))).strip()
        if md:
            parts.append(md)
        for i, img in enumerate(box.select("img[src*='pluginfile.php']"), 1):
            try:
                text = ocr.text(
                    client.http.get(urljoin(MOODLE_URL, img["src"]), timeout=30).content
                )
            except Exception as e:
                log.warning("      [ocr gagal] %s", e)
                continue
            if text.strip():
                parts.append(f"[Teks dari gambar soal {i} (OCR)]\n{text.strip()}")
    # Hanya lampiran soal dari dosen; file jawaban mahasiswa tidak diunduh.
    links = [
        a["href"]
        for a in soup.select("a[href*='pluginfile.php']")
        if re.search(r"/mod_(assign|quiz)/(intro|introattachment)/", a["href"])
    ]
    attachments = [save_attachment(client, url, cmid) for url in dict.fromkeys(links)]
    return "\n\n".join(parts), attachments


def summarize(task: dict, now: int) -> None:
    due = task.get("deadline_ts")
    task["lewat_deadline"] = bool(due and due < now)
    status = task["status"]
    if task["module"] == "assign":
        done = status.get("pengumpulan") == "submitted"
        if done:
            text = "Sudah dikumpulkan" + (
                " (terlambat)" if status.get("waktu") == "terlambat" else ""
            )
            if status.get("penilaian") == "sudah_dinilai":
                text += f", dinilai: {status.get('nilai') or '-'}"
        elif status.get("pengumpulan") == "draft":
            text = "Draft, BELUM dikirim untuk dinilai"
        elif status.get("pengumpulan") is None:
            text = "Status tidak diketahui (tugas mungkin belum dibuka)"
        else:
            text = "BELUM dikumpulkan"
    else:
        done = bool(status.get("percobaan"))
        text = "Sudah dikerjakan" if done else "Belum dikerjakan"
        if status.get("nilai"):
            text += f" ({status['nilai']})"
    if not done and task["lewat_deadline"]:
        text += " — LEWAT DEADLINE"
    task["sudah_dikumpulkan"] = done
    task["status_ringkas"] = text


def fetch_task(client: MoodleClient, task: dict, deadlines: dict, ocr: OcrCache, now: int) -> dict:
    soup = BeautifulSoup(client.get_page(task["url"]), "html.parser")
    dates = activity_dates(soup)
    calendar = deadlines.get(task["cmid"], {})
    due_ts = (
        calendar.get("due")
        or calendar.get("close")
        or parse_moodle_date(dates.get("Due") or dates.get("Closes") or dates.get("Closed") or "")
    )
    open_ts = calendar.get("open") or parse_moodle_date(
        dates.get("Opened") or dates.get("Opens") or dates.get("Allow submissions from") or ""
    )
    task.update(
        {
            "dibuka": ts_to_iso(open_ts),
            "deadline": ts_to_iso(due_ts),
            "deadline_ts": due_ts,
            "tanggal_asli": dates,
            "status": parse_assign(soup) if task["module"] == "assign" else parse_quiz(soup),
        }
    )
    task["deskripsi"], task["lampiran"] = task_description(soup, client, ocr, task["cmid"])
    summarize(task, now)
    task["diperbarui"] = datetime.now(WIB).isoformat(timespec="minutes")
    return task


def write_summary(tasks: list[dict], generated: str) -> None:
    def row(t: dict) -> str:
        return f"| {t.get('deadline') or '-'} | {t['matkul']} | {t['jenis']}: {t['judul']} | {t['status_ringkas']} |"

    pending = [t for t in tasks if not t["sudah_dikumpulkan"]]
    done = [t for t in tasks if t["sudah_dikumpulkan"]]
    lines = ["# Daftar Tugas & Kuis", "", f"Diperbarui: {generated} (WIB)", ""]
    for title, group in (("Belum dikumpulkan / dikerjakan", pending), ("Sudah dikumpulkan", done)):
        lines += [
            f"## {title} ({len(group)})",
            "",
            "| Deadline | Mata kuliah | Tugas | Status |",
            "|---|---|---|---|",
        ]
        lines += [row(t) for t in group] + [""]
    lines += ["## Detail", ""]
    for t in tasks:
        lines += [
            f"### {t['matkul']} — {t['judul']}",
            "",
            f"- Jenis: {t['jenis']}",
            f"- Pertemuan: {t['pertemuan'] or '-'} ({t['section']})",
            f"- Dibuka: {t.get('dibuka') or '-'}",
            f"- Deadline: {t.get('deadline') or '-'}",
            f"- Status: {t['status_ringkas']}",
            f"- Link: {t['url']}",
            "",
        ]
        if t["status"].get("file_dikumpulkan"):
            lines += ["File dikumpulkan: " + ", ".join(t["status"]["file_dikumpulkan"]), ""]
        if t.get("deskripsi"):
            lines += ["**Soal:**", "", t["deskripsi"], ""]
        lines += [
            f"Lampiran: {a['nama']} ({a.get('markdown') or a['path']})"
            for a in t.get("lampiran", [])
        ]
    write_text_atomic(SUMMARY_FILE, "\n".join(lines) + "\n")


def run(course_ids: list[str] | None = None) -> int:
    ASSIGNMENTS_DIR.mkdir(parents=True, exist_ok=True)
    previous = {t["cmid"]: t for t in read_json(ASSIGNMENTS_FILE).get("tugas", [])}
    client = MoodleClient()
    ocr = OcrCache()
    now = int(time.time())
    tasks, errors = [], 0
    try:
        courses = select_courses(client.enrolled_courses())
        if course_ids:
            courses = [c for c in courses if c["id"] in set(course_ids)]
        deadlines = calendar_deadlines(client)
        for course in courses:
            found = course_tasks(client, course)
            if found:
                log.info("=== %s: %d tugas/kuis", course["name"], len(found))
            for task in found:
                try:
                    tasks.append(fetch_task(client, task, deadlines, ocr, now))
                    log.info(
                        "  - %-45s %-17s %s",
                        task["judul"][:45],
                        task["deadline"] or "-",
                        task["status_ringkas"],
                    )
                except LoginRequired:
                    raise
                except Exception as e:
                    errors += 1
                    log.error("  [error] %s: %s", task["judul"], e)
                    if task["cmid"] in previous:  # data lama lebih baik daripada hilang
                        tasks.append(previous[task["cmid"]])
    except LoginRequired as e:
        log.error("[x] Sesi habis: %s. Login ulang: python -m edupad login", e)
        report_login_expired(MOODLE, "pengambil tugas")
        return EXIT_LOGIN_REQUIRED
    finally:
        ocr.save()
    report_login_ok(MOODLE)

    if course_ids:  # sebagian mata kuliah diperbarui: pertahankan data mata kuliah lain
        updated = {t["cmid"] for t in tasks}
        tasks += [
            t
            for cmid, t in previous.items()
            if cmid not in updated and t["course_id"] not in set(course_ids)
        ]
    tasks.sort(key=lambda t: (t["sudah_dikumpulkan"], t.get("deadline_ts") or NO_DEADLINE))
    generated = datetime.now(WIB).isoformat(timespec="minutes")
    write_json(ASSIGNMENTS_FILE, {"diperbarui": generated, "tugas": tasks})
    write_summary(tasks, generated)
    pending = sum(not t["sudah_dikumpulkan"] for t in tasks)
    log.info(
        "\n[selesai] %d tugas/kuis, %d belum dikumpulkan, %d error.", len(tasks), pending, errors
    )
    return EXIT_ERROR if errors else EXIT_OK
