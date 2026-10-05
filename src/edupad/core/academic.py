"""Aturan domain perkuliahan: nomor pertemuan, kelas, KRS."""

from __future__ import annotations

import re

from edupad.config import SCHEDULE_DIR
from edupad.core.files import read_json

SCHEDULE_FILE = SCHEDULE_DIR / "schedule.json"


def meeting_number(section: str, index: int | None) -> int | None:
    """Nomor pertemuan dari judul section; bila tidak ada, urutan section.

    "Pertemuan 5-Percabangan" -> 5, "03 - Monitoring" -> 3, section 0 ("General") -> None.
    """
    m = re.search(r"pertemuan\s*(\d+)", section or "", re.I) or re.match(r"\s*(\d+)\b", section or "")
    if m:
        return int(m.group(1))
    return index or None


def course_class(name: str) -> str | None:
    """'... - Kelas 5/B1' -> 'B'."""
    m = re.search(r"Kelas\s+\d+\s*/\s*([A-Za-z])", name)
    return m.group(1).upper() if m else None


def krs_classes() -> list[dict]:
    """Kelas yang diambil mahasiswa (hasil `edupad schedule`), [] bila belum ada."""
    return read_json(SCHEDULE_FILE).get("kelas", [])


def krs_course_ids() -> set[str]:
    return {k["moodle_course_id"] for k in krs_classes() if k.get("moodle_course_id")}
