from datetime import datetime, timedelta

import pytest

from edupad.agent import updates as u
from edupad.config import WIB

NOW = datetime(2026, 10, 14, 10, 0, tzinfo=WIB)  # Rabu
CATALOG = [
    {"course_id": "1", "matkul": "Pemrograman Visual", "kode": "TIF 1", "alias": ["pv", "tif1"]},
    {
        "course_id": "2",
        "matkul": "Praktikum Manajemen Sistem Basis Data",
        "kode": "TIF 2 P",
        "alias": ["prak msbd", "praktikum msbd"],
    },
]
KRS = [
    {"hari": "rabu", "mulai": "09:30", "selesai": "11:10", "matkul": "Pemrograman Visual",
     "nama_ruang": "Laboratorium Komputer", "ruang": "I09", "moodle_course_id": "1"},
    {"hari": "kamis", "mulai": "08:00", "selesai": "09:40", "matkul": "Praktikum Manajemen Sistem Basis Data",
     "ruang": "R.B.2", "moodle_course_id": "2"},
]  # fmt: skip


def meeting(mid, start, end, status=None, cara=("QR",)):
    return {"id": mid, "nama": "Pertemuan 5", "mulai": start.isoformat(), "selesai": end.isoformat(),
            "status": status, "dibuka": False, "cara": list(cara)}  # fmt: skip


@pytest.fixture
def data(monkeypatch):
    state = {
        "attendance": {"diperbarui": (NOW - timedelta(minutes=2)).isoformat(), "mata_kuliah": []},
        "tasks": [],
        "tasks_updated": (NOW - timedelta(minutes=5)).isoformat(),
        "expired": {},
    }
    monkeypatch.setattr(u, "_catalog", lambda: CATALOG)
    monkeypatch.setattr(u, "krs_classes", lambda: KRS)
    monkeypatch.setattr(u, "read_json", lambda path: state["attendance"])
    monkeypatch.setattr(
        u,
        "list_assignments",
        lambda only_pending: {"diperbarui": state["tasks_updated"], "tugas": state["tasks"]},
    )
    monkeypatch.setattr(u, "get_state", lambda service: state["expired"].get(service, {}))
    return state


def test_short_names_come_from_catalog_aliases(data):
    assert u.short_name("Praktikum Manajemen Sistem Basis Data", "2") == "Prak MSBD"
    assert u.short_name("[TIF 1] Pemrograman Visual - Kelas 5/B") == "PV"
    assert u.short_name("[ABC] Kelas Classroom - Kelas 5/B") == "Kelas Classroom"


def test_next_class_is_ongoing_or_soonest(data):
    ongoing = u.next_class(NOW)
    assert ongoing["name"] == "PV" and ongoing["ongoing"] and ongoing["day"] == "Hari ini"
    later = u.next_class(NOW + timedelta(hours=2))
    assert later["name"] == "Prak MSBD" and later["day"] == "Besok" and later["time"] == "08:00"
    assert later["room"] == "R.B.2" and not later["ongoing"]
    # setelah kelas Kamis lewat, kembali ke Rabu minggu depan
    assert u.next_class(datetime(2026, 10, 15, 12, 0, tzinfo=WIB))["day"] == "Rabu"


def test_attendance_open_and_recorded(data):
    data["attendance"]["mata_kuliah"] = [
        {"matkul": "Pemrograman Visual", "moodle_course_id": "1", "pertemuan": [
            meeting("a", NOW - timedelta(minutes=10), NOW + timedelta(minutes=20)),
            meeting("b", NOW - timedelta(minutes=30), NOW + timedelta(minutes=5), status="hadir"),
            meeting("c", NOW - timedelta(days=7), NOW - timedelta(days=7, hours=-1)),
        ]}
    ]  # fmt: skip
    alerts = u.attendance_alerts(NOW)
    assert [(a["id"], a["kind"]) for a in alerts] == [
        ("att:a", "attendance"),
        ("hadir:b", "attended"),
    ]
    assert alerts[0]["method"] == "qr" and alerts[0]["detail"] == "Laboratorium Komputer"
    assert alerts[0]["when"] == "Tutup 10:20"
    # data presensi lama (sesi SATU habis): tidak menebak
    data["attendance"]["diperbarui"] = (NOW - timedelta(hours=1)).isoformat()
    assert u.attendance_alerts(NOW) == []


def test_deadlines_within_48_hours_remind_daily_then_every_15_minutes(data):
    def task(title, due):
        return {"matkul": "[TIF 1] Pemrograman Visual - Kelas 5/B", "judul": title,
                "url": title, "deadline": due.isoformat() if due else None}  # fmt: skip

    data["tasks"] = [
        task("Laporan", NOW + timedelta(hours=30)),
        task("Kuis", NOW + timedelta(hours=2, minutes=5)),
        task("Nanti", NOW + timedelta(days=5)),
        task("Lewat", NOW - timedelta(hours=1)),
        task("Tanpa", None),
    ]
    alerts = u.deadline_alerts(NOW)
    assert [a["detail"] for a in alerts] == ["Kuis", "Laporan"]
    # Lebih dari 24 jam: sekali sehari. Sisanya dihitung per 15 menit sebelum deadline, jadi
    # sisa 2 jam 5 menit masih blok ke-8 dan pengingat berikutnya jatuh 5 menit lagi.
    assert alerts[0]["id"].endswith(":urgent8") and alerts[1]["id"].endswith(":2026-10-14")
    assert alerts[1]["when"] == "Besok 16:00" and alerts[0]["course"] == "PV"
    assert u.deadline_alerts(NOW + timedelta(minutes=4))[0]["id"] == alerts[0]["id"]
    assert u.deadline_alerts(NOW + timedelta(minutes=6))[0]["id"].endswith(":urgent7")


def test_updates_orders_alerts_and_reports_expired_sessions(data):
    data["expired"] = {"satu": {"expired_since": "2026-10-12T07:20:03+07:00"}}
    result = u.updates(NOW)
    assert result["now_ts"] == int(NOW.timestamp()) and result["stale"] == ["SATU"]
    assert result["next_class"]["name"] == "PV" and result["alerts"] == []


def test_stale_task_data_keeps_the_daily_reminder_but_drops_the_15_minute_repeats(data):
    data["tasks"] = [
        {"matkul": "[TIF 1] Pemrograman Visual - Kelas 5/B", "judul": "Kuis",
         "url": "Kuis", "deadline": (NOW + timedelta(hours=2, minutes=5)).isoformat()},
    ]  # fmt: skip
    assert u.deadline_alerts(NOW)[0]["id"].endswith(":urgent8")  # data segar: mendesak

    data["tasks_updated"] = (NOW - timedelta(hours=4)).isoformat()
    [alert] = u.deadline_alerts(NOW)
    assert alert["id"].endswith(":2026-10-14")  # basi: kembali sekali sehari
    # sekali sehari artinya pengecekan 15 menit kemudian tidak mengingatkan lagi
    assert u.deadline_alerts(NOW + timedelta(minutes=15))[0]["id"] == alert["id"]


def test_stale_task_sources_uses_a_threshold_per_source():
    base = {
        "diperbarui": (NOW - timedelta(minutes=30)).isoformat(),
        "classroom_diperbarui": (NOW - timedelta(hours=2)).isoformat(),
        "tugas": [{"judul": "kelas.usu"}, {"judul": "gc", "sumber": "Google Classroom"}],
    }
    # cron tugas 15 menit (ambang 1 jam), cron Classroom 2 jam (ambang 3 jam)
    assert u.stale_task_sources(base, NOW) == set()
    assert u.stale_task_sources(base | {"diperbarui": None}, NOW) == {None}
    lewat = (NOW - timedelta(hours=2)).isoformat()
    assert u.stale_task_sources(base | {"diperbarui": lewat}, NOW) == {None}
    assert u.stale_task_sources(base | {"classroom_diperbarui": None}, NOW) == {"Google Classroom"}
    # sumber yang tidak punya tugas tidak dilaporkan walau waktunya tidak ada
    assert u.stale_task_sources({"tugas": [], "diperbarui": None}, NOW) == set()
