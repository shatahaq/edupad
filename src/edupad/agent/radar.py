"""Radar belajar pribadi: satu sumber data untuk rencana belajar (suara), Equity Radar
(dashboard), dan pemberitahuan perangkat (GET /v1/updates).

Semua sinyal dihitung dari data EduPad yang nyata:
- penguasaan topik dari kuis lisan Tutor (`topic_mastery`, `learning_checks`);
- akses materi: pertemuan yang sudah berlangsung (presensi SATU) dibanding materi yang ada
  di kelas.usu/Classroom, materi hasil OCR, dan ringkasan yang bisa dibacakan;
- peringatan dini: kehadiran mendekati batas syarat ujian, deadline, anggaran.
"""

from __future__ import annotations

import json
import logging
import math
import os
import threading
import time
from datetime import datetime, timedelta

from edupad.config import WIB
from edupad.core.files import read_json

log = logging.getLogger(__name__)

DEFAULT_SEMESTER_MEETINGS = 16
DEFAULT_MIN_ATTENDANCE = 0.75
DEADLINE_SOON = timedelta(days=7)
REVIEW_HOURS = range(16, 22)  # pengingat mengulang hanya sore-malam WIB
MAX_REVIEWS = 3


def _now() -> datetime:
    return datetime.now(WIB)


def _float_env(name: str, default: float, low: float, high: float) -> float:
    try:
        return min(max(float(os.environ.get(name, default)), low), high)
    except ValueError:
        return default


def attendance_rules() -> tuple[int, float]:
    meetings = int(_float_env("EDUPAD_SEMESTER_MEETINGS", DEFAULT_SEMESTER_MEETINGS, 1, 32))
    minimum = _float_env("EDUPAD_MIN_ATTENDANCE", DEFAULT_MIN_ATTENDANCE, 0.0, 1.0)
    return meetings, minimum


def _parse(value: object) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=WIB)


# ------------------------------- kehadiran --------------------------------
def attendance_risk(now: datetime | None = None) -> list[dict]:
    """Per mata kuliah: hadir, tidak hadir, dan sisa jatah tidak hadir sebelum melewati batas."""
    from edupad.agent.tools import ATTENDANCE_FILE

    now = now or _now()
    default_total, minimum = attendance_rules()
    data = read_json(ATTENDANCE_FILE)
    rows = []
    for course in data.get("mata_kuliah", []):
        # SATU sering sudah mencantumkan seluruh pertemuan semester (tanpa tanggal).
        planned = len(course.get("pertemuan", []))
        total = planned if planned >= default_total * 0.75 else default_total
        allowed = max(0, math.floor(total * (1 - minimum) + 1e-9))
        held = [
            m
            for m in course.get("pertemuan", [])
            if (_parse(m.get("selesai")) or _parse(m.get("mulai")) or now) < now
        ]
        present = sum(str(m.get("status") or "").lower() == "hadir" for m in held)
        absent = len(held) - present
        remaining = allowed - absent
        level = "aman"
        if remaining < 0:
            level = "melewati"
        elif remaining <= 1:
            level = "waspada"
        rows.append(
            {
                "matkul": course.get("matkul") or "",
                "course_id": course.get("moodle_course_id"),
                "berlangsung": len(held),
                "hadir": present,
                "tidak_hadir": absent,
                "persen": round(present * 100 / len(held)) if held else None,
                "pertemuan_semester": total,
                "jatah_tidak_hadir": allowed,
                "sisa_jatah": remaining,
                "status": level,
                "diperbarui": data.get("diperbarui"),
            }
        )
    rows.sort(key=lambda r: (r["sisa_jatah"], r["matkul"]))
    return rows


# ------------------------------ akses materi ------------------------------
def access_audit(now: datetime | None = None) -> dict:
    """Kesenjangan akses materi per mata kuliah (pertemuan berlangsung vs materi tersedia)."""
    from edupad.agent.tools import (
        ATTENDANCE_FILE,
        CORPUS_DIR,
        _catalog,
        _classroom,
        resolve_course,
    )
    from edupad.processing.summaries import get_summary

    now = now or _now()
    chunks_file = CORPUS_DIR / "chunks.jsonl"
    ocr: dict[str, set[int]] = {}
    try:
        with chunks_file.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("ocr"):
                    for m in row.get("pertemuan") or []:
                        ocr.setdefault(str(row.get("course_id")), set()).add(int(m))
    except (OSError, ValueError):
        pass

    classroom_meetings: dict[str, set[int]] = {}
    classroom_items: dict[str, int] = {}
    for data in _classroom():
        names = {k["course_id"]: k.get("nama") or "" for k in data.get("kelas", [])}
        for item in data.get("materi", []):
            course = resolve_course(names.get(item.get("course_id")) or item.get("matkul"))
            if not course:
                continue
            classroom_items[course["course_id"]] = classroom_items.get(course["course_id"], 0) + 1
            if isinstance(item.get("pertemuan"), int):
                classroom_meetings.setdefault(course["course_id"], set()).add(item["pertemuan"])

    held_by_course: dict[str, list[dict]] = {}
    for course in read_json(ATTENDANCE_FILE).get("mata_kuliah", []):
        held_by_course[str(course.get("moodle_course_id"))] = [
            m
            for m in course.get("pertemuan", [])
            if (_parse(m.get("mulai")) or now + timedelta(days=1)) <= now
            and isinstance(m.get("pertemuan"), int)
        ]

    courses = []
    for c in _catalog():
        cid = str(c["course_id"])
        moodle = {int(k) for k in c.get("pertemuan", {}) if str(k).isdigit()}
        available = moodle | classroom_meetings.get(cid, set())
        held = held_by_course.get(cid, [])
        held_numbers = sorted({m["pertemuan"] for m in held})
        missing = [
            {"pertemuan": m["pertemuan"], "topik": m.get("topik")}
            for m in sorted(held, key=lambda m: m["pertemuan"])
            if m["pertemuan"] not in available
        ]
        summarized = sorted(m for m in moodle if get_summary(cid, str(m)))
        courses.append(
            {
                "matkul": c["matkul"],
                "course_id": cid,
                "jenis": c.get("jenis"),
                "pertemuan_berlangsung": len(held_numbers),
                "pertemuan_bermateri": len(available),
                "materi_classroom": classroom_items.get(cid, 0),
                "tanpa_materi": missing,
                "ocr": sorted(ocr.get(cid, set())),
                "bisa_didengar": len(summarized),
                "status": (
                    "belum_ada_materi"
                    if not available
                    else "ada_kekosongan"
                    if missing
                    else "lengkap"
                ),
            }
        )
    courses.sort(key=lambda c: (-len(c["tanpa_materi"]), c["pertemuan_bermateri"], c["matkul"]))
    held_total = sum(c["pertemuan_berlangsung"] for c in courses)
    missing_total = sum(len(c["tanpa_materi"]) for c in courses)
    with_material = sum(c["pertemuan_bermateri"] for c in courses)
    return {
        "mata_kuliah": courses,
        "jumlah_mata_kuliah": len(courses),
        "tanpa_materi_sama_sekali": sum(c["status"] == "belum_ada_materi" for c in courses),
        "pertemuan_berlangsung": held_total,
        "pertemuan_tanpa_materi": missing_total,
        "cakupan_persen": round((held_total - missing_total) * 100 / held_total)
        if held_total
        else None,
        "pertemuan_bermateri": with_material,
        "pertemuan_ocr": sum(len(c["ocr"]) for c in courses),
        "bisa_didengar": sum(c["bisa_didengar"] for c in courses),
    }


# ------------------------------- penguasaan -------------------------------
def mastery_overview(now: datetime | None = None) -> dict:
    """Penguasaan topik & aktivitas kuis; kosong (available=False) bila tabel belum ada."""
    from edupad.agent.tutor import MASTERED_FROM, WEAK_BELOW, TutorStore, TutorUnavailable

    now = now or _now()
    try:
        store = TutorStore()
        topics = store.mastery()
        checks = store.checks(since=now - timedelta(days=30))
    except TutorUnavailable as e:
        return {"available": False, "reason": str(e), "topics": [], "courses": [], "checks": []}
    rows = []
    for t in topics:
        due_at = _parse(t.get("next_review_at"))
        rows.append(
            {
                "matkul": t["course"],
                "course_id": t.get("course_id"),
                "pertemuan": t.get("meeting"),
                "judul": t.get("title") or "",
                "penguasaan": round(float(t.get("mastery") or 0) * 100),
                "kuis": int(t.get("attempts") or 0),
                "skor_terakhir": round(float(t.get("last_score") or 0) * 100),
                "terakhir": t.get("last_checked_at"),
                "ulang_pada": t.get("next_review_at"),
                "jatuh_tempo": bool(due_at and due_at <= now),
            }
        )
    rows.sort(key=lambda r: (r["penguasaan"], r["matkul"]))
    per_course: dict[str, list[int]] = {}
    for r in rows:
        per_course.setdefault(r["matkul"], []).append(r["penguasaan"])
    week = [c for c in checks if (_parse(c.get("created_at")) or now) >= now - timedelta(days=7)]
    misconceptions: dict[str, int] = {}
    for c in checks:
        if c.get("misconception"):
            key = str(c["misconception"]).strip()
            misconceptions[key] = misconceptions.get(key, 0) + 1
    return {
        "available": True,
        "topics": rows,
        "courses": [
            {"matkul": name, "penguasaan": round(sum(v) / len(v)), "topik": len(v)}
            for name, v in sorted(per_course.items(), key=lambda kv: sum(kv[1]) / len(kv[1]))
        ],
        "dikuasai": sum(r["penguasaan"] >= MASTERED_FROM * 100 for r in rows),
        "lemah": sum(r["penguasaan"] < WEAK_BELOW * 100 for r in rows),
        "jatuh_tempo": sum(r["jatuh_tempo"] for r in rows),
        "rata_rata": round(sum(r["penguasaan"] for r in rows) / len(rows)) if rows else None,
        "soal_30_hari": len(checks),
        "soal_7_hari": len(week),
        "skor_7_hari": round(sum(float(c["score"]) for c in week) * 100 / len(week))
        if week
        else None,
        "miskonsepsi": [
            {"teks": text, "jumlah": n}
            for text, n in sorted(misconceptions.items(), key=lambda kv: -kv[1])[:8]
        ],
        "checks": [
            {
                "matkul": c["course"],
                "pertemuan": c.get("meeting"),
                "soal": c["question"],
                "jawaban": c.get("answer") or "",
                "penilaian": c["verdict"],
                "umpan_balik": c.get("feedback") or "",
                "waktu": c.get("created_at"),
            }
            for c in checks[:30]
        ],
    }


# ----------------------------- peringatan dini ----------------------------
def early_warnings(now: datetime | None = None) -> list[dict]:
    """Sinyal yang perlu ditindaklanjuti, dengan kalimat ajakan (bukan vonis)."""
    from edupad.agent.finance import FinanceStore, FinanceUnavailable, rupiah
    from edupad.agent.tools import list_assignments

    now = now or _now()
    warnings: list[dict] = []
    for row in attendance_risk(now):
        if row["status"] == "aman" or not row["berlangsung"]:
            continue
        text = (
            f"Di SATU, {row['tidak_hadir']} dari {row['berlangsung']} pertemuan {row['matkul']} "
            f"belum tercatat hadir, melewati batas {row['jatah_tidak_hadir']} kali. Cek ke dosen "
            "bila ada yang keliru atau cari jalan keluarnya."
            if row["status"] == "melewati"
            else f"Jatah tidak hadir {row['matkul']} tinggal {row['sisa_jatah']} kali. "
            "Usahakan hadir di pertemuan berikutnya."
        )
        warnings.append(
            {
                "jenis": "kehadiran",
                "tingkat": "tinggi" if row["status"] == "melewati" else "sedang",
                "matkul": row["matkul"],
                "pesan": text,
                "kunci": f"hadir:{row['course_id']}:{row['tidak_hadir']}",
                "sisa": row["sisa_jatah"],
                "data_diperbarui": row["diperbarui"],
            }
        )
    for task in list_assignments(only_pending=True).get("tugas", []):
        due = _parse(task.get("deadline"))
        if not due:
            continue
        if due < now and now - due <= timedelta(days=14):
            warnings.append(
                {
                    "jenis": "tugas_terlewat",
                    "tingkat": "sedang",
                    "matkul": task["matkul"],
                    "pesan": f"Tugas '{task['judul']}' sudah lewat deadline. Tanyakan ke dosen "
                    "apakah masih bisa dikumpulkan.",
                    "kunci": f"lewat:{task.get('url') or task['judul']}",
                }
            )
    try:
        for b in FinanceStore().budget_status(now.date()):
            if b["persen"] is None or b["persen"] < 90:
                continue
            warnings.append(
                {
                    "jenis": "anggaran",
                    "tingkat": "tinggi" if b["sisa"] < 0 else "sedang",
                    "matkul": None,
                    "pesan": (
                        f"Anggaran {b['kategori']} bulan ini terlampaui {rupiah(-b['sisa'])}."
                        if b["sisa"] < 0
                        else f"Anggaran {b['kategori']} tinggal {rupiah(b['sisa'])} "
                        f"({b['persen']}% terpakai)."
                    ),
                    "kunci": f"anggaran:{b['kategori']}:{now:%Y-%m}:{'lewat' if b['sisa'] < 0 else '90'}",
                    "kategori": b["kategori"],
                    "sisa": b["sisa"],
                }
            )
    except FinanceUnavailable:
        pass
    order = {"tinggi": 0, "sedang": 1}
    warnings.sort(key=lambda w: order.get(w["tingkat"], 2))
    return warnings


# ------------------------------ rencana belajar ---------------------------
def _next_meeting_topic(course_id: str | None, when: datetime) -> dict | None:
    from edupad.agent.tools import ATTENDANCE_FILE

    for course in read_json(ATTENDANCE_FILE).get("mata_kuliah", []):
        if str(course.get("moodle_course_id")) != str(course_id):
            continue
        for m in course.get("pertemuan", []):
            start = _parse(m.get("mulai"))
            if start and start.date() == when.date():
                return {"pertemuan": m.get("pertemuan"), "topik": m.get("topik")}
    return None


def study_plan(now: datetime | None = None) -> dict:
    from edupad.agent.formatting import to_display_text
    from edupad.agent.tools import list_assignments
    from edupad.agent.updates import next_class
    from edupad.core.academic import krs_classes

    now = now or _now()
    plan: dict = {"waktu": now.isoformat()}
    upcoming = next_class(now)
    if upcoming:
        start = datetime.fromtimestamp(upcoming["start_ts"], WIB)
        course_id = next(
            (
                k.get("moodle_course_id")
                for k in krs_classes()
                if to_display_text(k.get("matkul") or "") == upcoming["course"]
            ),
            None,
        )
        plan["kuliah_berikutnya"] = {
            "matkul": upcoming["course"],
            "hari": upcoming["day"],
            "jam": upcoming["time"],
            "ruang": upcoming["room"],
            "sedang_berlangsung": upcoming["ongoing"],
            **(_next_meeting_topic(course_id, start) or {}),
        }
    mastery = mastery_overview(now)
    if mastery["available"]:
        due = [t for t in mastery["topics"] if t["jatuh_tempo"]]
        plan["perlu_diulang"] = [
            {k: t[k] for k in ("matkul", "pertemuan", "judul", "penguasaan")}
            for t in due[:MAX_REVIEWS]
        ]
        plan["topik_lemah"] = [
            {k: t[k] for k in ("matkul", "pertemuan", "judul", "penguasaan")}
            for t in mastery["topics"]
            if t["penguasaan"] < 60 and not t["jatuh_tempo"]
        ][:MAX_REVIEWS]
        plan["progres"] = {
            "topik_dikuasai": mastery["dikuasai"],
            "topik_dinilai": len(mastery["topics"]),
            "soal_7_hari": mastery["soal_7_hari"],
            "skor_7_hari_persen": mastery["skor_7_hari"],
        }
    else:
        plan["catatan_tutor"] = "data kuis belum tersedia"
    deadlines = []
    for task in list_assignments(only_pending=True).get("tugas", []):
        due_at = _parse(task.get("deadline"))
        if due_at and now <= due_at <= now + DEADLINE_SOON:
            deadlines.append(
                {"matkul": task["matkul"], "judul": task["judul"], "deadline": task["deadline"]}
            )
    deadlines.sort(key=lambda t: t["deadline"])
    plan["deadline_7_hari"] = deadlines[:5]
    plan["peringatan"] = [w["pesan"] for w in early_warnings(now)][:4]
    return plan


# --------------------------- pemberitahuan perangkat -----------------------
def _help_card(now: datetime, to_display_text) -> dict | None:
    """Kartu sore untuk bantuan yang disiapkan SORA (memakai tampilan kartu "review")."""
    from edupad.agent import coach
    from edupad.agent.tutor import TutorStore, TutorUnavailable
    from edupad.agent.updates import short_name

    try:
        h = coach.current_help(TutorStore())
    except TutorUnavailable:
        return None
    if not h or h["status"] != "siap":
        return None
    before = h.get("mastery_before")
    return {
        "id": f"help:{h['id']}:{now.date().isoformat()}",
        "kind": "review",
        "course": to_display_text(f"{short_name(h['course'], h.get('course_id'))} P{h['meeting']}"),
        "detail": to_display_text(f"SORA siapkan bantuan: {h['title']}"),
        "when": f"Penguasaan {round(before * 100)}%" if before is not None else "Pelajaran + kuis",
        "from_ts": 0,
        "to_ts": 0,
        "speech": f"SORA sudah menyiapkan pelajaran singkat tentang {h['title']}, "
        f"{h['course']} pertemuan {h['meeting']}. Ucapkan mulai untuk memulai.",
    }


_alerts_cache: tuple[float, str, list[dict]] | None = None
_alerts_lock = threading.Lock()
ALERTS_CACHE_SECONDS = 300  # perangkat bertanya tiap 2 menit; Supabase cukup dibaca tiap 5 menit


def device_alerts(now: datetime | None = None, cached: bool = True) -> list[dict]:
    """Kartu tambahan untuk /v1/updates: pengingat mengulang (kind "review") dan peringatan
    dini (kind "warning"). id berganti per hari agar tidak berulang terus di hari yang sama."""
    global _alerts_cache
    now = now or _now()
    slot = f"{now:%Y-%m-%d %H}"
    with _alerts_lock:
        entry = _alerts_cache
    if cached and entry and entry[1] == slot and time.monotonic() - entry[0] < ALERTS_CACHE_SECONDS:
        return entry[2]
    try:
        alerts = _device_alerts(now)
    except Exception:  # noqa: BLE001 - kartu tambahan tidak boleh menggagalkan /v1/updates
        log.exception("[radar] pemberitahuan tambahan gagal dihitung")
        alerts = []
    with _alerts_lock:
        _alerts_cache = (time.monotonic(), slot, alerts)
    return alerts


def _device_alerts(now: datetime) -> list[dict]:
    from edupad.agent.formatting import to_display_text
    from edupad.agent.updates import short_name

    alerts: list[dict] = []
    for w in early_warnings(now):
        if w["jenis"] not in {"kehadiran", "anggaran"}:
            continue
        if w["jenis"] == "kehadiran":
            course = short_name(w["matkul"])
            detail = (
                "Batas kehadiran terlewati" if w["sisa"] < 0 else f"Sisa jatah absen {w['sisa']}x"
            )
        else:
            course = f"Anggaran {w['kategori']}"
            detail = "Sudah terlampaui" if w["sisa"] < 0 else "Hampir habis"
        alerts.append(
            {
                "id": f"warn:{w['kunci']}:{now.date().isoformat()}",
                "kind": "warning",
                "course": to_display_text(course),
                "detail": to_display_text(detail),
                "when": "Peringatan",
                "from_ts": 0,
                "to_ts": 0,
                "level": "high" if w["tingkat"] == "tinggi" else "medium",
                "speech": f"Peringatan. {w['pesan']}",
            }
        )
    if now.hour in REVIEW_HOURS:
        help_card = _help_card(now, to_display_text)
        if help_card:  # bantuan SORA menggantikan pengingat biasa hari itu
            alerts.append(help_card)
            return alerts
        mastery = mastery_overview(now)
        due = [t for t in mastery.get("topics", []) if t["jatuh_tempo"]]
        if due:
            t = due[0]
            meeting = f" P{t['pertemuan']}" if t.get("pertemuan") is not None else ""
            alerts.append(
                {
                    "id": f"review:{t['course_id'] or t['matkul']}:{t['pertemuan']}:"
                    f"{now.date().isoformat()}",
                    "kind": "review",
                    "course": to_display_text(
                        short_name(t["matkul"], t.get("course_id")) + meeting
                    ),
                    "detail": to_display_text(t["judul"] or "Waktunya mengulang"),
                    "when": f"Penguasaan {t['penguasaan']}%",
                    "from_ts": 0,
                    "to_ts": 0,
                    "count": len(due),
                    "speech": f"Waktunya mengulang {t['judul'] or t['matkul']}"
                    + (f", {t['matkul']} pertemuan {t['pertemuan']}" if t.get("pertemuan") else "")
                    + f". Penguasaanmu {t['penguasaan']} persen. Ucapkan uji aku lagi untuk kuis.",
                }
            )
    return alerts
