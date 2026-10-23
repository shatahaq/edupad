import json
from datetime import datetime, timedelta

from edupad.agent import memory as memory_mod
from edupad.agent import tools
from edupad.agent.assistant import SEEN_NOTE, Usage, dedupe
from edupad.agent.evaluate import check_turn
from edupad.agent.memory import ConversationMemory, format_sources, turn_messages
from edupad.config import WIB
from fakes import FakeDb


def _row(i, matkul="PV", meetings=(1,)):
    return {
        "id": f"c{i}",
        "matkul": matkul,
        "pertemuan": list(meetings),
        "judul": f"j{i}",
        "isi": "x" * 50,
    }


def test_fusion_promotes_item_ranked_high_by_both():
    rows = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    # hybrid: a, b, c; reranker: c paling relevan, lalu b
    fused = tools.fuse_rankings(rows, scores=[0.1, 0.5, 0.9])
    assert [r["id"] for r in fused][0] in {"b", "c"}
    assert {r["id"] for r in fused} == {"a", "b", "c"}


def test_dedupe_hides_repeated_chunks():
    seen = set()
    first = dedupe("search_materials", {"hasil": [_row(1), _row(2)]}, seen)
    second = dedupe("search_materials", {"hasil": [_row(2), _row(3)]}, seen)
    assert all(r["isi"] != SEEN_NOTE for r in first["hasil"])
    assert second["hasil"][0]["isi"] == SEEN_NOTE and second["hasil"][0]["judul"] == "j2"
    assert second["hasil"][1]["isi"] != SEEN_NOTE


def test_dedupe_hides_chunks_of_meeting_already_sent_in_full():
    seen = set()
    dedupe("get_meeting", {"matkul": "PV", "pertemuan": 4, "isi": "seluruh materi"}, seen)
    result = dedupe(
        "search_materials", {"hasil": [_row(1, meetings=(4,)), _row(2, meetings=(5,))]}, seen
    )
    assert [r["isi"] == SEEN_NOTE for r in result["hasil"]] == [True, False]
    again = dedupe("get_meeting", {"matkul": "PV", "pertemuan": 4, "isi": "seluruh materi"}, seen)
    assert again["isi"] == SEEN_NOTE


def test_meeting_summary_does_not_count_as_full_text():
    seen = set()
    dedupe("get_meeting", {"matkul": "PV", "pertemuan": 4, "ringkasan": "..."}, seen)
    result = dedupe("search_materials", {"hasil": [_row(1, meetings=(4,))]}, seen)
    assert result["hasil"][0]["isi"] != SEEN_NOTE


def test_answer_schema_without_detail():
    with_detail = tools.answer_schema(True)["function"]["parameters"]
    without = tools.answer_schema(False)["function"]["parameters"]
    assert "detail" in with_detail["required"] and "detail" not in without["required"]
    assert "detail" not in without["properties"]
    assert (
        "detail" in tools.answer_schema(True)["function"]["parameters"]["properties"]
    )  # tidak termutasi


def test_usage_cost_separates_cache_hits():
    usage = Usage()
    usage.add(
        {
            "prompt_tokens": 1000,
            "prompt_cache_hit_tokens": 800,
            "prompt_cache_miss_tokens": 200,
            "completion_tokens": 100,
            "completion_tokens_details": {"reasoning_tokens": 30},
        }
    )
    assert usage.as_dict() == {
        "calls": 1,
        "total": 1100,
        "cache_hit": 800,
        "cache_miss": 200,
        "output": 100,
        "reasoning": 30,
        "cost_usd": round((800 * 0.006 + 200 * 0.30 + 100 * 1.2) / 1e6, 6),
    }


def test_turn_messages_use_answer_tool_call():
    sources = [{"matkul": "PV", "pertemuan": [4], "judul": "Operator"}] * 3
    user, assistant, tool = turn_messages(
        "apa itu xor?",
        "Xor benar bila tepat satu.",
        ["- Xor: satu benar"],
        sources,
        call_id="riwayat_7",
    )
    assert user == {"role": "user", "content": "apa itu xor?"}
    call = assistant["tool_calls"][0]
    assert (
        call["id"] == tool["tool_call_id"] == "riwayat_7" and call["function"]["name"] == "answer"
    )
    assert json.loads(call["function"]["arguments"]) == {
        "speech": "Xor benar bila tepat satu.",
        "screen_lines": ["Xor: satu benar"],
    }
    assert "Layar" not in assistant["content"] and tool["content"].endswith(
        "sumber: PV p4: Operator"
    )
    assert format_sources(sources) == "PV p4: Operator"


def test_fallback_never_speaks_screen_or_sources():
    from edupad.agent.formatting import fallback_answer

    text = "Maaf, data presensi tidak ada.\nLayar: Data tidak tersedia | Cek portal\nSumber: -"
    answer = fallback_answer(text)
    assert answer["speech"] == "Maaf, data presensi tidak ada."
    assert answer["screen"]["lines"] == ["- Data tidak tersedia", "- Cek portal"]


def test_attendance_for_day_and_recap(monkeypatch, tmp_path):
    from edupad.core.files import write_json

    meeting = {"nama": "Pertemuan 7", "topik": "WBS", "dibuka": False, "cara": ["QR"]}
    write_json(
        tmp_path / "attendance.json",
        {
            "diperbarui": datetime.now(WIB).isoformat(),
            "mata_kuliah": [
                {
                    "matkul": "Manajemen Proyek IT",
                    "kelas": "B",
                    "moodle_course_id": "38410",
                    "pertemuan": [
                        {
                            **meeting,
                            "nama": "Pertemuan 6",
                            "mulai": "2026-09-24T16:50+07:00",
                            "selesai": None,
                            "status": "hadir",
                        },
                        {
                            **meeting,
                            "mulai": "2026-10-01T16:52+07:00",
                            "selesai": "2026-10-01T17:00+07:00",
                            "status": None,
                        },
                        {
                            **meeting,
                            "nama": "Pertemuan 8",
                            "mulai": None,
                            "selesai": None,
                            "status": None,
                        },
                    ],
                }
            ],
        },
    )
    monkeypatch.setattr(tools, "ATTENDANCE_FILE", tmp_path / "attendance.json")
    monkeypatch.setattr(
        tools,
        "_catalog",
        lambda: [
            {
                "course_id": "38410",
                "matkul": "Manajemen Proyek IT",
                "alias": ["mpit"],
                "pertemuan": {},
            }
        ],
    )
    result = tools.get_attendance(course="mpit", date="2026-10-01")
    assert [
        (m["pertemuan"], m["status"], m["mulai"]) for m in result["pertemuan_pada_tanggal"]
    ] == [("Pertemuan 7", "belum diisi", "16:52")]
    assert result["rekap"] == [
        {"matkul": "Manajemen Proyek IT", "kelas": "B", "hadir": 1, "pertemuan_sampai_tanggal": 2}
    ]
    assert "peringatan" not in result
    assert "error" in tools.get_attendance(course="kimia")


def test_presence_window_states():
    now = datetime(2026, 10, 1, 16, 55, tzinfo=WIB)
    base = {
        "status": None,
        "dibuka": False,
        "mulai": "2026-10-01T16:52+07:00",
        "selesai": "2026-10-01T17:00+07:00",
    }
    assert tools.presence_window(base, now) == "sedang dibuka"
    assert tools.presence_window(base, now + timedelta(minutes=10)).startswith("sudah tutup")
    assert tools.presence_window(base, now - timedelta(minutes=10)) == "belum dibuka"
    assert tools.presence_window({**base, "status": "hadir"}, now) == "sudah diisi"
    assert (
        tools.presence_window({**base, "mulai": None, "selesai": None}, now) == "belum dijadwalkan"
    )


def test_check_turn_scores_sources_keywords_and_not_found():
    result = {
        "speech": "Materinya belum ada.",
        "screen": {"lines": []},
        "detail": "",
        "sources": [{"course_id": "38408", "pertemuan": [4]}],
        "tools": [{"tool": "search_materials"}],
    }
    checks = check_turn(
        {
            "sources": [["38408", 4]],
            "keywords": ["xor|operator", "belum"],
            "not_found": True,
            "tools": ["list_assignments"],
        },
        result,
    )
    assert checks == {"sumber": True, "kata_kunci": 0.5, "tools": False, "mengaku_tidak_ada": True}


def _result(i):
    return {
        "speech": f"jawaban {i}",
        "screen": {"lines": [f"poin {i}"]},
        "detail": "",
        "sources": [{"matkul": "PV", "pertemuan": [i], "judul": f"materi {i}"}],
        "usage": {},
    }


def test_memory_persists_turns_and_reuses_recent_session():
    db = FakeDb()
    first = ConversationMemory("u1", new_session=True, db=db)
    first.save_turn("apa itu xor?", _result(1))
    second = ConversationMemory("u1", db=db)
    assert second.session["id"] == first.session["id"]
    assert [m["content"] for m in second.history()][0] == "apa itu xor?"


def test_history_carries_actions_so_they_are_not_repeated():
    """Tanpa jejak ini agent "menyusul" mencatat ulang transaksi dari giliran sebelumnya."""
    db = FakeDb()
    mem = ConversationMemory("u1", new_session=True, db=db)
    mem.save_turn(
        "tadi beli ayam geprek dua puluh ribu",
        _result(1) | {"actions": ["catat pengeluaran Makan Rp20.000 (2026-10-22)"]},
    )
    tool_result = ConversationMemory("u1", db=db).history()[2]
    assert tool_result["role"] == "tool"
    assert "sudah dijalankan: catat pengeluaran Makan Rp20.000" in tool_result["content"]


def test_memory_starts_new_session_after_idle():
    db = FakeDb()
    first = ConversationMemory("u1", new_session=True, db=db)
    old = (datetime.now(WIB) - memory_mod.SESSION_IDLE - timedelta(minutes=1)).isoformat()
    db.update("agent_sessions", {"last_active": old}, id=f"eq.{first.session['id']}")
    assert ConversationMemory("u1", db=db).session["id"] != first.session["id"]


def test_memory_summarizes_old_turns_and_keeps_recent_ones():
    db = FakeDb()
    mem = ConversationMemory("u1", new_session=True, db=db)
    for i in range(memory_mod.SUMMARIZE_AFTER):
        mem.save_turn(f"tanya {i}", _result(i))
    prompts = []

    def complete(prompt):
        prompts.append(prompt)
        return '{"ringkasan": "membahas PV", "fakta_pengguna": ["suka contoh kode"]}'

    assert mem.maybe_summarize(complete)
    history = ConversationMemory("u1", db=db).history()
    assert history[0] == {
        "role": "system",
        "content": "Ringkasan percakapan sebelumnya di sesi ini: membahas PV",
    }
    assert len(history) == 1 + 3 * memory_mod.KEEP_TURNS  # pertanyaan, panggilan answer, hasil tool
    assert "tanya 0" in prompts[0] and "tanya 7" not in prompts[0]
    assert mem.facts() == ["suka contoh kode"]
    assert not mem.maybe_summarize(complete)  # sisa giliran belum cukup untuk diringkas lagi


def test_remember_skips_duplicates():
    mem = ConversationMemory("u1", new_session=True, db=FakeDb())
    assert mem.remember("Suka  contoh kode") == {"status": "disimpan"}
    assert mem.remember("suka contoh kode") == {"status": "sudah diingat"}
    assert mem.facts() == ["Suka contoh kode"]
