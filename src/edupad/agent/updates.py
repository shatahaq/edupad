"""Ringkasan untuk layar perangkat (GET /v1/updates): kuliah berikutnya dan pemberitahuan
(presensi dibuka / sudah tercatat, deadline tugas dekat).

Hanya membaca data hasil cron (jadwal, presensi, tugas), jadi murah dipanggil perangkat setiap
beberapa menit. Semua teks sudah ASCII untuk font LCD; waktu dikirim sebagai detik epoch
(hitung mundur di perangkat) dan sebagai label siap tampil ("Besok 23:59").
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, time, timedelta

from edupad.agent.formatting import to_display_text
from edupad.agent.tools import ATTENDANCE_FILE, _catalog, list_assignments, presence_window
from edupad.config import WIB
from edupad.core.academic import krs_classes
from edupad.core.files import read_json
from edupad.core.session import MOODLE, SATU, get_state

DAYS = ["senin", "selasa", "rabu", "kamis", "jumat", "sabtu", "minggu"]
DAY_LABELS = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
DEADLINE_WINDOW = timedelta(hours=48)  # tugas belum dikumpulkan yang deadline-nya sedekat ini
URGENT_DEADLINE = timedelta(hours=3)  # diingatkan sekali lagi
ATTENDANCE_FRESH = timedelta(minutes=15)  # cron presensi berjalan tiap 2 menit di jam kuliah
ATTENDED_SHOWN = timedelta(hours=2)  # "presensi tercatat" tampil selama pertemuan berlangsung
MAX_ALERTS = 5


def short_name(matkul: str, course_id: str | None = None) -> str:
    """'Praktikum Manajemen Sistem Basis Data' -> 'Prak MSBD' (alias terpendek di katalog)."""
    catalog = _catalog()
    code = re.match(r"\[(.+?)\]", matkul or "")
    course = next(
        (
            c
            for c in catalog
            if (course_id and c["course_id"] == course_id) or (code and c["kode"] == code[1])
        ),
        None,
    ) or next((c for c in catalog if c["matkul"].lower() == (matkul or "").lower()), None)
    if not course:
        name = re.sub(r"^\[.+?\]\s*|\s+-\s+Kelas\s+\S+$", "", matkul or "")
        return to_display_text(name)
    aliases = [a for a in course["alias"] if not a.replace(" ", "").startswith("tif")]
    pick = min(aliases or [course["matkul"]], key=len)
    return " ".join(
        w.upper() if len(w) <= 4 and w != "prak" else w.capitalize() for w in pick.split()
    )


def day_label(when: datetime, now: datetime) -> str:
    days = (when.date() - now.date()).days
    if days == 0:
        return "Hari ini"
    if days == 1:
        return "Besok"
    return DAY_LABELS[when.weekday()]


def _room(course_id: str | None) -> str:
    k = next((k for k in krs_classes() if course_id and k.get("moodle_course_id") == course_id), {})
    return to_display_text(k.get("nama_ruang") or k.get("ruang") or "")


def next_class(now: datetime) -> dict | None:
    """Kelas yang sedang berlangsung, atau yang mulai paling dekat (dari jadwal mingguan KRS)."""
    best = None
    for k in krs_classes():
        if k.get("hari") not in DAYS or not k.get("mulai") or not k.get("selesai"):
            continue
        ahead = (DAYS.index(k["hari"]) - now.weekday()) % 7
        for days in (ahead, ahead + 7):
            date = (now + timedelta(days=days)).date()
            start = datetime.combine(date, time.fromisoformat(k["mulai"]), WIB)
            end = datetime.combine(date, time.fromisoformat(k["selesai"]), WIB)
            if end > now:
                if best is None or start < best[0]:
                    best = (start, end, k)
                break
    if best is None:
        return None
    start, end, k = best
    return {
        "name": short_name(k["matkul"], k.get("moodle_course_id")),
        "course": to_display_text(k["matkul"]),
        "room": to_display_text(k.get("nama_ruang") or k.get("ruang") or ""),
        "room_code": k.get("ruang") or "",
        "day": day_label(start, now),
        "time": start.strftime("%H:%M"),
        "start_ts": int(start.timestamp()),
        "end_ts": int(end.timestamp()),
        "ongoing": start <= now,
    }


def attendance_alerts(now: datetime) -> list[dict]:
    """Presensi yang sedang dibuka dan belum diisi, serta yang baru saja tercatat (mis. diisi
    otomatis server). Dilewati bila data presensi sudah lama (sesi SATU habis)."""
    data = read_json(ATTENDANCE_FILE)
    updated = data.get("diperbarui")
    if not updated or now - datetime.fromisoformat(updated) > ATTENDANCE_FRESH:
        return []
    alerts = []
    for course in data.get("mata_kuliah", []):
        for m in course.get("pertemuan", []):
            if not m.get("mulai"):
                continue
            start = datetime.fromisoformat(m["mulai"])
            end = datetime.fromisoformat(m["selesai"]) if m.get("selesai") else None
            base = {
                "course": short_name(course["matkul"], course.get("moodle_course_id")),
                "detail": _room(course.get("moodle_course_id"))
                or to_display_text(m.get("nama") or ""),
                "from_ts": int(start.timestamp()),
                "to_ts": int(end.timestamp()) if end else 0,
            }
            if not m.get("status") and presence_window(m, now) == "sedang dibuka":
                cara = m.get("cara") or []
                alerts.append(
                    base
                    | {
                        "id": f"att:{m['id']}",
                        "kind": "attendance",
                        "when": f"Tutup {end:%H:%M}" if end else "Sedang dibuka",
                        "method": "direct" if "langsung" in cara else "qr",
                    }
                )
            elif m.get("status") == "hadir" and start <= now <= (end or start) + ATTENDED_SHOWN:
                alerts.append(
                    base
                    | {"id": f"hadir:{m['id']}", "kind": "attended", "when": m.get("nama") or ""}
                )
    return alerts


def deadline_alerts(now: datetime) -> list[dict]:
    """Tugas belum dikumpulkan (kelas.usu dan Classroom) yang deadline-nya dalam 48 jam.
    id berganti tiap hari dan saat tinggal 3 jam, sehingga perangkat mengingatkan lagi."""
    alerts = []
    for t in list_assignments(only_pending=True)["tugas"]:
        if not t.get("deadline"):
            continue
        due = datetime.fromisoformat(t["deadline"])
        left = due - now
        if not timedelta(0) < left <= DEADLINE_WINDOW:
            continue
        key = hashlib.sha1(f"{t.get('url')}|{t['judul']}".encode()).hexdigest()[:10]
        phase = "urgent" if left <= URGENT_DEADLINE else now.date().isoformat()
        alerts.append(
            {
                "id": f"due:{key}:{phase}",
                "kind": "deadline",
                "course": short_name(t["matkul"]),
                "detail": to_display_text(t["judul"]),
                "when": f"{day_label(due, now)} {due:%H:%M}",
                "from_ts": 0,
                "to_ts": int(due.timestamp()),
            }
        )
    alerts.sort(key=lambda a: a["to_ts"])
    return alerts


def stale_sources() -> list[str]:
    """Sumber data yang sesinya habis (datanya tidak diperbarui sampai login ulang)."""
    labels = {SATU: "SATU", MOODLE: "kelas.usu"}
    return [label for service, label in labels.items() if get_state(service).get("expired_since")]


def updates(now: datetime | None = None, extra_cards: bool = False) -> dict:
    """`extra_cards`: perangkat mengenal kartu "warning" & "review" (firmware yang mengirim
    X-Firmware); firmware lama akan menampilkan jenis tak dikenal sebagai deadline."""
    now = now or datetime.now(WIB)
    alerts = attendance_alerts(now)
    from edupad.agent.radar import device_alerts

    # peringatan dini & pengingat mengulang (Tutor/Equity Radar)
    extra = device_alerts(now) if extra_cards else []
    alerts = (
        [a for a in alerts if a["kind"] == "attendance"]
        + deadline_alerts(now)
        + [a for a in extra if a["kind"] == "warning"]
        + [a for a in alerts if a["kind"] == "attended"]
        + [a for a in extra if a["kind"] == "review"]
    )
    return {
        "now_ts": int(now.timestamp()),
        "next_class": next_class(now),
        "alerts": alerts[:MAX_ALERTS],
        "stale": stale_sources(),
    }
