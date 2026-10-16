import json
from datetime import datetime, timedelta

import pytest
from tests.test_tutor_finance import Db

from edupad.agent import coach, radar, tools, tutor
from edupad.config import WIB

KEY = "38404:2"
COURSE = {"course_id": "38404", "matkul": "Manajemen Sistem Basis Data", "pertemuan": {"2": {}}}
BANK = [
    {"pertanyaan": f"Soal {level} {i}", "kunci": "k", "konsep": "c", "level": level}
    for level in ("lanjut", "menengah", "dasar")
    for i in (1, 2)
]
HELP_JSON = {
    "judul": "Normalisasi 3NF",
    "masalah": "Masih tertukar antara 2NF dan 3NF",
    "pelajaran": [
        {"ucapan": f"Bagian {i}", "layar_judul": f"Bagian {i}", "layar": ["poin"]}
        for i in (1, 2, 3)
    ],
    "soal": [{"pertanyaan": f"Soal terarah {i}", "kunci": "k", "konsep": "3NF"} for i in (1, 2, 3)],
}


@pytest.fixture
def db(monkeypatch, tmp_path):
    fake = Db()
    fake.tables["tutor_help"] = []
    real = tutor.TutorStore.__init__
    monkeypatch.setattr(
        tutor.TutorStore,
        "__init__",
        lambda self, user_id=None, db=None: real(self, user_id or "u1", fake),
    )
    monkeypatch.setattr(tutor, "_cache", {})
    monkeypatch.setattr(coach, "_cache", {})
    monkeypatch.setattr(tutor, "BANK_FILE", tmp_path / "bank.json")
    monkeypatch.setattr(tools, "resolve_course", lambda name: COURSE if name else None)
    monkeypatch.setattr(tutor, "_key_for", lambda course, meeting: (KEY, COURSE))
    source = {
        "course": COURSE["matkul"],
        "course_id": "38404",
        "meeting": 2,
        "title": "x",
        "text": "materi",
    }
    monkeypatch.setattr(tutor, "_quiz_source", lambda c, m, t: source)
    monkeypatch.setattr(coach, "_quiz_source", lambda c, m, t: source)
    return fake


def _no_llm(*args, **kwargs):
    raise AssertionError("AI tidak boleh dipanggil: soal ada di bank")


# --------------------------------- bank soal ---------------------------------
def test_quiz_uses_bank_without_ai_and_skips_recent_questions(db, monkeypatch):
    tutor._bank_add(KEY, "Database Engine", BANK)
    monkeypatch.setattr(tutor, "_generate", _no_llm)
    first = tutor.start_quiz("msbd", 2, count=2)
    assert first["pertanyaan"] == "Soal dasar 1"  # belum pernah diuji: mulai dari dasar
    tutor.answer_quiz("a", "benar", "ok")
    tutor.answer_quiz("b", "benar", "ok")
    second = tutor.start_quiz("msbd", 2, count=2)
    assert second["pertanyaan"] not in {"Soal dasar 1", "Soal dasar 2"}  # tidak mengulang


def test_bank_is_filled_once_when_empty(db, monkeypatch):
    calls = []

    def generate(source, count):
        calls.append(count)
        return "Database Engine", BANK

    monkeypatch.setattr(tutor, "_generate", generate)
    assert tutor.start_quiz("msbd", 2, count=3)["kuis_dimulai"]
    assert calls == [tutor.BANK_BATCH]
    assert len(tutor.bank_entry(KEY)["soal"]) == 6


def test_difficulty_follows_mastery():
    asked: set[str] = set()
    assert tutor.pick_questions(BANK, 1, asked, None)[0]["level"] == "dasar"
    assert tutor.pick_questions(BANK, 1, asked, 0.65)[0]["level"] == "menengah"
    assert tutor.pick_questions(BANK, 1, asked, 0.9)[0]["level"] == "lanjut"


def test_quiz_note_forgives_speech_recognition_errors(db, monkeypatch):
    tutor._bank_add(KEY, "Database Engine", BANK)
    monkeypatch.setattr(tutor, "_generate", _no_llm)
    tutor.start_quiz("msbd", 2)
    note = tutor.context_note("u1")
    assert "salah dengar" in note and "Kamu:" in note


# ------------------------------ tutor mandiri --------------------------------
def _seed_struggle(db):
    now = datetime.now(WIB)
    for verdict in ("salah", "sebagian"):
        db.insert(
            "learning_checks",
            [
                {
                    "user_id": "u1",
                    "quiz_id": "q0",
                    "topic_key": KEY,
                    "course": COURSE["matkul"],
                    "course_id": "38404",
                    "meeting": 2,
                    "question": "Apa itu 3NF?",
                    "expected": "k",
                    "answer": "sama dengan 2NF",
                    "verdict": verdict,
                    "score": 0.0,
                    "misconception": "tertukar 2NF dan 3NF",
                }
            ],
        )
    db.tables["topic_mastery"].append(
        {
            "user_id": "u1",
            "topic_key": KEY,
            "course": COURSE["matkul"],
            "course_id": "38404",
            "meeting": 2,
            "title": "Normalisasi",
            "mastery": 0.3,
            "attempts": 1,
            "next_review_at": (now + timedelta(days=1)).isoformat(),
            "interval_days": 1,
        }
    )
    # topik lain: hanya ditanyakan berulang (satu jenis sinyal) -> belum dianggap sulit
    for days in (1, 2, 3):
        db.insert(
            "agent_turns",
            [
                {
                    "user_id": "u1",
                    "question": "pertemuan 3 bahas apa",
                    "created_at": (now - timedelta(days=days)).isoformat(),
                    "sources": [
                        {"course_id": "38404", "matkul": COURSE["matkul"], "pertemuan": [3]}
                    ],
                }
            ],
        )


def test_needs_two_kinds_of_signals(db):
    _seed_struggle(db)
    found = coach.struggles(tutor.TutorStore())
    assert [t["topic_key"] for t in found] == [KEY]
    assert set(found[0]["kinds"]) == {"kuis", "penguasaan"}
    assert "penguasaan 30%" in found[0]["reasons"]


def test_saying_not_understood_twice_counts(db):
    now = datetime.now(WIB)
    for days in (1, 4):
        db.insert(
            "agent_turns",
            [
                {
                    "user_id": "u1",
                    "question": "aku masih belum paham normalisasi",
                    "created_at": (now - timedelta(days=days)).isoformat(),
                    "sources": [
                        {"course_id": "38404", "matkul": COURSE["matkul"], "pertemuan": [2]}
                    ],
                }
            ],
        )
    found = coach.struggles(tutor.TutorStore())
    assert found and found[0]["kinds"] == ["bingung"]


def test_coach_prepares_help_and_measures_before_after(db, monkeypatch):
    import edupad.agent.assistant as assistant

    _seed_struggle(db)
    monkeypatch.setattr(assistant, "_complete_json", lambda prompt: json.dumps(HELP_JSON))
    assert coach.run() == 0
    [plan] = db.tables["tutor_help"]
    assert plan["status"] == "siap" and plan["mastery_before"] == 0.3
    assert any("tertukar antara 2NF dan 3NF" in m["content"] for m in db.tables["agent_memories"])
    note = tutor.context_note("u1")
    assert "BANTUAN SIAP" in note and "Normalisasi 3NF" in note

    monkeypatch.setattr(radar, "_device_alerts", radar._device_alerts)
    card = radar._help_card(datetime.now(WIB), lambda s: s)
    assert card["kind"] == "review" and "Normalisasi 3NF" in card["detail"]

    assert coach.start_help()["ucapan"] == "Bagian 1"
    assert "SESI BANTUAN" in tutor.context_note("u1")
    assert coach.continue_help()["ucapan"] == "Bagian 2"
    assert coach.continue_help()["bagian"] == 3
    quiz = coach.continue_help()
    assert quiz["kuis_dimulai"] and quiz["pertanyaan"] == "Soal terarah 1"
    for _ in range(3):
        tutor.answer_quiz("jawaban benar", "benar", "Tepat")
    [plan] = db.tables["tutor_help"]
    assert plan["status"] == "selesai" and plan["mastery_after"] > plan["mastery_before"]
    assert coach.run() == 0 and len(db.tables["tutor_help"]) == 1  # baru dibantu: tidak diulang


def test_declined_help_waits_before_offering_again(db, monkeypatch):
    import edupad.agent.assistant as assistant

    _seed_struggle(db)
    monkeypatch.setattr(assistant, "_complete_json", lambda prompt: json.dumps(HELP_JSON))
    coach.run()
    assert coach.decline_help()["ditunda"]
    assert tutor.context_note("u1") is None
    coach.run()
    assert len(db.tables["tutor_help"]) == 1


def test_help_can_be_started_on_request(db, monkeypatch):
    import edupad.agent.assistant as assistant

    monkeypatch.setattr(assistant, "_complete_json", lambda prompt: json.dumps(HELP_JSON))
    part = coach.start_help("msbd", 2)
    assert part["bagian"] == 1 and db.tables["tutor_help"][0]["reasons"] == ["diminta mahasiswa"]


def test_dashboard_shows_learning_curve_and_help_effect(db, monkeypatch):
    import edupad.agent.assistant as assistant
    from edupad.office import dashboard_data

    _seed_struggle(db)
    db.tables["learning_checks"].clear()
    tutor._bank_add(KEY, "Database Engine", BANK)
    monkeypatch.setattr(tutor, "_generate", _no_llm)
    tutor.start_quiz("msbd", 2, count=2)
    tutor.answer_quiz("x", "salah", "")
    tutor.answer_quiz("y", "sebagian", "")
    db.tables["learning_checks"].append(dict(db.tables["learning_checks"][0], verdict="salah"))
    monkeypatch.setattr(assistant, "_complete_json", lambda prompt: json.dumps(HELP_JSON))
    coach.run()
    coach.start_help()
    for _ in range(3):
        coach.continue_help()
    for _ in range(3):
        tutor.answer_quiz("benar", "benar", "")
    panel = dashboard_data.tutor_panel()
    [curve] = panel["history"]
    assert [p["skor"] for p in curve["titik"]] == [17, 100]  # (0 + 0,5 + 0) / 3, lalu 3/3
    assert [p["bantuan"] for p in curve["titik"]] == [False, True]
    [help_row] = panel["help"]
    assert help_row["status"] == "selesai" and help_row["sesudah"] > help_row["sebelum"]
    assert help_row["pelajaran"] == ["Bagian 1", "Bagian 2", "Bagian 3"]
