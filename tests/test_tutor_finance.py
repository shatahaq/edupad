import json
from datetime import datetime, timedelta

import pytest
from tests.fakes import FakeDb

from edupad.agent import finance, radar, tools, tutor
from edupad.config import WIB
from edupad.core.supabase import SupabaseError


class Db(FakeDb):
    """FakeDb + tabel keuangan/tutor dan upsert yang benar-benar menimpa."""

    KEYS = {"finance_budgets": ("user_id", "category"), "topic_mastery": ("user_id", "topic_key")}

    def __init__(self):
        super().__init__()
        for name in (
            "finance_transactions",
            "finance_budgets",
            "tutor_quizzes",
            "learning_checks",
            "topic_mastery",
        ):
            self.tables[name] = []

    def insert(self, table, rows):
        now = datetime.now(WIB).isoformat()
        rows = [{"created_at": now, **r} for r in rows]
        return super().insert(table, rows)

    def upsert(self, table, rows, on_conflict):
        keys = self.KEYS[table]
        for row in rows:
            self.tables[table] = [
                r for r in self.tables[table] if any(r.get(k) != row.get(k) for k in keys)
            ]
            self.tables[table].append(dict(row))


@pytest.fixture
def db(monkeypatch):
    fake = Db()
    real_finance, real_tutor = finance.FinanceStore.__init__, tutor.TutorStore.__init__

    def finance_init(self, user_id=None, db=None):
        real_finance(self, user_id or "u1", fake)

    def tutor_init(self, user_id=None, db=None):
        real_tutor(self, user_id or "u1", fake)

    monkeypatch.setattr(finance.FinanceStore, "__init__", finance_init)
    monkeypatch.setattr(tutor.TutorStore, "__init__", tutor_init)
    monkeypatch.setattr(tutor, "_cache", {})
    return fake


# --------------------------------- keuangan --------------------------------
def test_voice_transaction_is_recorded_with_budget_and_can_be_undone(db):
    assert finance.set_budget("makan", 500_000)["nominal_teks"] == "Rp500.000"
    rec = finance.record_transaction("pengeluaran", 25_000, "makan siang", "nasi goreng")
    assert rec["kategori"] == "Makan" and rec["nominal_teks"] == "Rp25.000"
    assert rec["anggaran"]["sisa"] == 475_000
    assert db.tables["finance_transactions"][0]["source"] == "suara"

    finance.FinanceStore().add("income", 1_000_000, "Kiriman keluarga")  # dari dashboard
    summary = finance.finance_summary("bulan_ini")
    assert (summary["pemasukan"], summary["pengeluaran"], summary["saldo"]) == (
        1_000_000,
        25_000,
        975_000,
    )
    undone = finance.undo_last_transaction()
    assert undone["dihapus"] and undone["nominal_teks"] == "Rp25.000"  # bukan yang dashboard
    assert [r["source"] for r in db.tables["finance_transactions"]] == ["dashboard"]
    assert "error" in finance.undo_last_transaction()


def test_finance_rejects_bad_input_and_reports_missing_table(db, monkeypatch):
    assert "error" in finance.record_transaction("pengeluaran", 0, "Makan")
    assert "error" in finance.record_transaction("hutang", 5_000, "Makan")
    future = (datetime.now(WIB) + timedelta(days=5)).date().isoformat()
    assert "error" in finance.record_transaction("pengeluaran", 5_000, "Makan", date=future)
    assert (
        finance.record_transaction("pemasukan", 50_000, "gaji kerja sampingan")["kategori"]
        == "Kerja sampingan"
    )

    def missing(*args, **kwargs):
        raise SupabaseError('HTTP 404: {"code":"PGRST205"}')

    monkeypatch.setattr(db, "insert", missing)
    assert "belum dibuat" in finance.record_transaction("pengeluaran", 5_000, "Makan")["error"]


def test_period_ranges():
    today = datetime(2026, 10, 15).date()  # Kamis
    assert finance.period_range("minggu_ini", today) == (datetime(2026, 10, 12).date(), today)
    assert finance.period_range("bulan_lalu", today) == (
        datetime(2026, 9, 1).date(),
        datetime(2026, 9, 30).date(),
    )


# ---------------------------------- tutor ----------------------------------
QUESTIONS = [
    {
        "pertanyaan": "Apa itu buffer pool?",
        "kunci": "cache halaman data di memori",
        "konsep": "buffer pool",
    },
    {"pertanyaan": "Mengapa WAL penting?", "kunci": "durability", "konsep": "WAL"},
]


@pytest.fixture
def quiz_source(monkeypatch):
    monkeypatch.setattr(
        tutor,
        "_quiz_source",
        lambda course, meeting, topic: {
            "course": "Manajemen Sistem Basis Data",
            "course_id": "38404",
            "meeting": 2,
            "title": "Database Engine",
            "text": "materi",
        },
    )
    monkeypatch.setattr(tutor, "_generate", lambda source, count: ("Database Engine", QUESTIONS))


def test_quiz_flow_updates_mastery_and_schedules_review(db, quiz_source):
    started = tutor.start_quiz("msbd", 2)
    assert started["pertanyaan"] == "Apa itu buffer pool?" and started["jumlah_soal"] == 2
    note = tutor.context_note("u1")
    assert "soal 1/2" in note and "cache halaman data di memori" in note

    first = tutor.answer_quiz("cache di memori", "benar", "Tepat")
    assert first["berikutnya"]["pertanyaan"] == "Mengapa WAL penting?"
    assert "soal 2/2" in tutor.context_note("u1")

    last = tutor.answer_quiz("tidak tahu", "salah", "Kuncinya durability")
    final = last["hasil_akhir"]
    assert (final["benar"], final["skor_persen"], final["diulang_lagi_dalam_hari"]) == (1, 50, 2)
    assert final["perlu_diperkuat"] == ["WAL"]
    assert tutor.context_note("u1") is None
    mastery = db.tables["topic_mastery"]
    assert len(mastery) == 1 and mastery[0]["mastery"] == 0.5
    assert "error" in tutor.answer_quiz("lagi", "benar", "")


def test_quiz_without_topic_uses_due_review(db, quiz_source):
    assert "error" in tutor.start_quiz()  # belum ada topik
    past = (datetime.now(WIB) - timedelta(hours=1)).isoformat()
    db.tables["topic_mastery"].append(
        {
            "user_id": "u1",
            "topic_key": "38404:2",
            "course": "Manajemen Sistem Basis Data",
            "course_id": "38404",
            "meeting": 2,
            "title": "x",
            "mastery": 0.4,
            "next_review_at": past,
            "interval_days": 1,
            "attempts": 1,
        }
    )
    assert tutor.start_quiz()["kuis_dimulai"]


def test_stop_quiz_counts_answered_questions(db, quiz_source):
    tutor.start_quiz("msbd", 2)
    tutor.answer_quiz("cache di memori", "benar", "Tepat")
    stopped = tutor.stop_quiz()
    assert stopped["dihentikan"] and stopped["dinilai"] == 1 and stopped["skor_persen"] == 100
    assert db.tables["tutor_quizzes"][0]["status"] == "stopped"


def test_review_intervals_grow_only_when_mastered():
    assert [tutor.next_interval(None, 1.0), tutor.next_interval(3, 0.9)] == [1, 7]
    assert tutor.next_interval(30, 1.0) == 30
    assert tutor.next_interval(7, 0.5) == 2 and tutor.next_interval(7, 0.2) == 1


def test_agent_offers_tutor_and_finance_tools():
    for name in ("start_quiz", "answer_quiz", "study_plan", "record_transaction", "set_budget"):
        assert name in tools.TOOLS


# ---------------------------------- radar ----------------------------------
def _attendance(path, statuses, planned=16):
    now = datetime.now(WIB)
    meetings = []
    for i in range(planned):
        when = now - timedelta(days=7 * (len(statuses) - i)) if i < len(statuses) else None
        meetings.append(
            {
                "id": str(i),
                "pertemuan": i + 1,
                "nama": f"Pertemuan {i + 1}",
                "mulai": when.isoformat() if when else "",
                "selesai": (when + timedelta(hours=2)).isoformat() if when else None,
                "topik": f"Topik {i + 1}",
                "status": statuses[i] if i < len(statuses) else None,
                "dibuka": False,
                "cara": [],
            }
        )
    path.write_text(
        json.dumps(
            {
                "diperbarui": now.isoformat(),
                "mata_kuliah": [
                    {
                        "matkul": "Basis Data",
                        "kode": "X",
                        "kelas": "A",
                        "moodle_course_id": "1",
                        "pertemuan": meetings,
                    }
                ],
            }
        )
    )


def test_attendance_risk_counts_remaining_absences(tmp_path, monkeypatch):
    path = tmp_path / "attendance.json"
    monkeypatch.setattr(tools, "ATTENDANCE_FILE", path)
    _attendance(path, ["hadir", None, None, "hadir", None])
    row = radar.attendance_risk()[0]
    assert (row["berlangsung"], row["tidak_hadir"], row["jatah_tidak_hadir"]) == (5, 3, 4)
    assert row["sisa_jatah"] == 1 and row["status"] == "waspada"
    _attendance(path, [None] * 5)
    assert radar.attendance_risk()[0]["status"] == "melewati"
