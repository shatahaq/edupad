import json
import time
from dataclasses import replace
from datetime import datetime, timedelta

import pytest

from edupad.agent import tools
from edupad.collectors import classroom
from edupad.config import WIB, get_settings
from edupad.errors import EXIT_ERROR, EXIT_LOGIN_REQUIRED, EXIT_OK
from edupad.google import oauth
from edupad.google.accounts import AccountStore

NOW = datetime(2026, 10, 12, 12, 0, tzinfo=WIB)
NOW_TS = int(NOW.timestamp())


# ------------------------------ normalisasi ----------------------------------
def test_due_date_is_utc_converted_to_wib():
    work = {
        "dueDate": {"year": 2026, "month": 10, "day": 15},
        "dueTime": {"hours": 16, "minutes": 59},
    }
    assert classroom.due(work) == (
        "2026-10-15T23:59+07:00",
        int(datetime(2026, 10, 15, 23, 59, tzinfo=WIB).timestamp()),
    )
    # proto3 JSON menghilangkan 0: 00:00 UTC datang sebagai dueTime {}
    midnight = {"dueDate": {"year": 2026, "month": 10, "day": 15}, "dueTime": {}}
    assert classroom.due(midnight)[0] == "2026-10-15T07:00+07:00"
    assert classroom.due({}) == (None, None)
    assert classroom.due({"dueDate": {"year": 2026, "month": 2, "day": 30}}) == (None, None)
    assert classroom.to_wib("2026-10-01T03:04:05.123Z") == "2026-10-01T10:04+07:00"
    assert classroom.to_wib(None) is None and classroom.to_wib("bukan tanggal") is None


def test_attachments_cover_every_material_type():
    materials = [
        {
            "driveFile": {
                "driveFile": {
                    "id": "d1",
                    "title": "Modul 1.pdf",
                    "alternateLink": "https://drive/d1",
                }
            }
        },
        {"youtubeVideo": {"id": "y", "title": "Video", "alternateLink": "https://youtu.be/y"}},
        {"link": {"url": "https://contoh.id"}},
        {"form": {"title": "Kuis", "formUrl": "https://forms/f"}},
        {"gem": {"id": "g", "title": "Tutor", "url": "https://gemini/g"}},
        {"tidak_dikenal": {}},
    ]
    assert classroom.attachments(materials) == [
        {"jenis": "drive", "judul": "Modul 1.pdf", "url": "https://drive/d1", "drive_id": "d1"},
        {"jenis": "youtube", "judul": "Video", "url": "https://youtu.be/y"},
        {"jenis": "tautan", "judul": "https://contoh.id", "url": "https://contoh.id"},
        {"jenis": "form", "judul": "Kuis", "url": "https://forms/f"},
        {"jenis": "gem", "judul": "Tutor", "url": "https://gemini/g"},
    ]
    assert classroom.attachments(None) == []


def test_task_status_matches_usu_wording():
    past = {
        "dueDate": {"year": 2026, "month": 10, "day": 1},
        "dueTime": {"hours": 1},
        "maxPoints": 100,
    }
    future = {"dueDate": {"year": 2026, "month": 12, "day": 1}, "dueTime": {"hours": 1}}
    cases = [
        (future, {"state": "TURNED_IN"}, "Sudah dikumpulkan", True),
        (past, {"state": "TURNED_IN", "late": True}, "Sudah dikumpulkan (terlambat)", True),
        (
            past,
            {"state": "RETURNED", "assignedGrade": 90.0},
            "Sudah dikembalikan guru, nilai: 90/100",
            True,
        ),
        (future, {"state": "CREATED"}, "BELUM dikumpulkan", False),
        (past, {"state": "NEW"}, "BELUM dikumpulkan — LEWAT DEADLINE", False),
        (
            past,
            {"state": "RECLAIMED_BY_STUDENT"},
            "Ditarik kembali, BELUM dikumpulkan — LEWAT DEADLINE",
            False,
        ),
        ({}, None, "Status tidak diketahui", False),
    ]
    for work, submission, text, done in cases:
        status = classroom.task_status(work, submission, NOW_TS)
        assert (status["status_ringkas"], status["sudah_dikumpulkan"]) == (text, done), text


def test_meeting_number_from_topic_or_title():
    assert classroom.meeting_of("Pertemuan 3 - Basis Data", "Tugas") == 3
    assert classroom.meeting_of("05. Normalisasi", "Tugas") == 5
    assert classroom.meeting_of(None, "Kuis pertemuan 7") == 7
    assert classroom.meeting_of(None, "2 Soal Latihan") is None  # angka di judul bukan pertemuan
    assert classroom.meeting_of("Umum", "Silabus") is None


def test_paged_follows_tokens_and_stops(monkeypatch):
    calls = []

    def fake_get(token, path, params):
        calls.append(params.get("pageToken"))
        page = int(params.get("pageToken") or 0)
        return {"items": [page], "nextPageToken": str(page + 1)}  # tidak pernah selesai

    monkeypatch.setattr(classroom, "_get", fake_get)
    assert classroom.paged("t", "/x", "items", {}, limit=3) == [0, 1, 2]
    calls.clear()
    assert len(classroom.paged("t", "/x", "items", {})) == classroom.MAX_PAGES  # pengaman


# ------------------------------- sinkronisasi --------------------------------
class FakeApi:
    """Classroom API tiruan: path -> respons JSON, mencatat setiap panggilan."""

    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def __call__(self, url, params=None, headers=None, timeout=None):
        path = url.removeprefix(classroom.API_URL)
        self.calls.append((path, dict(params or {}), headers))
        status, body = self.routes.get(path, (404, {"error": {"message": "tidak ada"}}))
        return FakeResponse(status, body)


class FakeResponse:
    def __init__(self, status, body):
        self.status_code, self.ok, self._body, self.text = (
            status,
            status < 400,
            body,
            json.dumps(body),
        )

    def json(self):
        return self._body


COURSE = {
    "id": "c1",
    "name": "Basis Data",
    "section": "Kelas A",
    "alternateLink": "https://classroom/c1",
}
ROUTES = {
    "/courses": (200, {"courses": [COURSE]}),
    "/courses/c1/topics": (200, {"topic": [{"topicId": "t1", "name": "Pertemuan 2"}]}),
    "/courses/c1/courseWork": (
        200,
        {
            "courseWork": [
                {
                    "id": "w1",
                    "title": "Tugas ERD",
                    "workType": "ASSIGNMENT",
                    "topicId": "t1",
                    "dueDate": {"year": 2026, "month": 10, "day": 20},
                    "dueTime": {"hours": 16, "minutes": 59},
                    "alternateLink": "https://classroom/w1",
                    "description": "Buat ERD perpustakaan",
                },
                {"id": "w2", "title": "Kuis cepat", "workType": "MULTIPLE_CHOICE_QUESTION"},
            ]
        },
    ),
    "/courses/c1/courseWork/-/studentSubmissions": (
        200,
        {
            "studentSubmissions": [
                {"courseWorkId": "w1", "state": "CREATED"},
                {"courseWorkId": "w2", "state": "TURNED_IN"},
            ]
        },
    ),
    "/courses/c1/courseWorkMaterials": (
        200,
        {
            "courseWorkMaterial": [
                {
                    "id": "m1",
                    "title": "Slide Normalisasi",
                    "topicId": "t1",
                    "creationTime": "2026-10-05T01:00:00Z",
                    "materials": [
                        {
                            "driveFile": {
                                "driveFile": {
                                    "id": "d",
                                    "title": "normalisasi.pdf",
                                    "alternateLink": "https://drive/d",
                                }
                            }
                        }
                    ],
                },
            ]
        },
    ),
    "/courses/c1/announcements": (
        403,
        {"error": {"message": "The caller does not have permission"}},
    ),
}


@pytest.fixture
def env(tmp_path, monkeypatch):
    settings = replace(
        get_settings(),
        google_client_id="id",
        google_client_secret="s",
        user_id="default",
        owner_emails=frozenset({"siswa@gmail.com"}),
    )
    store = AccountStore(tmp_path / "accounts.json", tmp_path / "lock")
    store.save_login(
        {"sub": "111", "email": "siswa@gmail.com", "name": "Siti"},
        oauth.Tokens("at", time.time() + 3600, "rt", frozenset(oauth.SCOPES), None),
        "default",
    )
    monkeypatch.setattr(classroom, "get_settings", lambda: settings)
    monkeypatch.setattr(classroom, "CLASSROOM_DIR", tmp_path / "classroom")
    monkeypatch.setattr(classroom, "AccountStore", lambda: store)
    api = FakeApi(dict(ROUTES))
    monkeypatch.setattr(classroom.http_pool, "get", api)
    return {"store": store, "api": api, "dir": tmp_path / "classroom", "settings": settings}


def test_sync_account_writes_usu_compatible_data(env):
    client = oauth.Client("id", "s", "http://x/cb")
    data = classroom.sync_account(env["store"], client, env["store"].get("111"), now=lambda: NOW)
    saved = json.loads((env["dir"] / "111.json").read_text())
    assert saved == data and data["user_id"] == "default" and data["email"] == "siswa@gmail.com"
    assert (env["dir"] / "111.json").stat().st_mode & 0o777 == 0o600
    assert (
        data["kelas"][0]["course_id"] == "gc-c1"
        and "basis data kelas a" in data["kelas"][0]["alias"]
    )
    erd, quiz = data["tugas"]  # bertenggat dulu, tanpa tenggat di akhir
    assert (
        erd["deadline"] == "2026-10-20T23:59+07:00"
        and erd["pertemuan"] == 2
        and erd["topik"] == "Pertemuan 2"
    )
    assert erd["status_ringkas"] == "BELUM dikumpulkan" and erd["sumber"] == "Google Classroom"
    assert quiz["jenis"] == "pertanyaan" and quiz["sudah_dikumpulkan"] and quiz["deadline"] is None
    assert (
        data["materi"][0]["judul"] == "Slide Normalisasi"
        and data["materi"][0]["lampiran"][0]["jenis"] == "drive"
    )
    assert data["error"] and "pengumuman" in data["error"][0]  # 403 dicatat, tidak fatal
    path, params, headers = env["api"].calls[0]
    assert path == "/courses" and params["studentId"] == "me" and params["courseStates"] == "ACTIVE"
    assert headers == {"Authorization": "Bearer at"}
    submissions = next(p for path, p, _ in env["api"].calls if path.endswith("studentSubmissions"))
    assert submissions["userId"] == "me"


def test_legacy_coursework_scope_still_fetches_tasks(env):
    legacy = {
        oauth.CLASSROOM_COURSES,
        "https://www.googleapis.com/auth/classroom.student-submissions.me.readonly",
    }
    env["store"].save_login(
        {"sub": "111", "email": "siswa@gmail.com"},
        oauth.Tokens("at", time.time() + 3600, "rt", frozenset(legacy), None),
        "default",
    )
    data = classroom.sync_account(
        env["store"], oauth.Client("id", "s", "x"), env["store"].get("111"), now=lambda: NOW
    )
    assert [t["judul"] for t in data["tugas"]] == ["Tugas ERD", "Kuis cepat"]
    assert data["tugas"][0]["status_ringkas"] == "BELUM dikumpulkan"  # pengumpulan ikut terbaca


def test_scopes_not_granted_are_skipped(env):
    env["store"].save_login(
        {"sub": "111", "email": "siswa@gmail.com"},
        oauth.Tokens("at", time.time() + 3600, None, frozenset({oauth.CLASSROOM_COURSES}), None),
        "default",
    )
    client = oauth.Client("id", "s", "http://x/cb")
    data = classroom.sync_account(env["store"], client, env["store"].get("111"), now=lambda: NOW)
    assert (
        [c[0] for c in env["api"].calls] == ["/courses"]
        and data["tugas"] == []
        and data["error"] == []
    )


def test_run_reports_each_account(env, monkeypatch):
    assert classroom.run() == EXIT_OK and (env["dir"] / "111.json").exists()
    assert classroom.run(email="orang-lain@gmail.com") == EXIT_OK  # tidak ada akun itu
    env["api"].routes["/courses"] = (500, {"error": {"message": "backend error"}})
    assert classroom.run() == EXIT_ERROR

    def revoked(sub, client):
        raise oauth.ReauthRequired("invalid_grant", "invalid_grant")

    monkeypatch.setattr(env["store"], "access_token", revoked)
    assert classroom.run() == EXIT_LOGIN_REQUIRED
    monkeypatch.setattr(
        classroom, "get_settings", lambda: replace(env["settings"], google_client_id=None)
    )
    assert classroom.run() == EXIT_ERROR


def test_accounts_without_classroom_permission_are_skipped(env):
    env["store"].save_login(
        {"sub": "111", "email": "siswa@gmail.com"},
        oauth.Tokens("at", time.time() + 3600, "rt", frozenset({"openid", "email"}), None),
        "default",
    )
    assert classroom.run() == EXIT_OK and env["api"].calls == []


def test_other_endpoint_errors_fail_the_sync(env):
    env["api"].routes["/courses/c1/courseWork"] = (500, {"error": {"message": "backend error"}})
    with pytest.raises(classroom.ClassroomError, match="500"):
        classroom.sync_account(env["store"], oauth.Client("id", "s", "x"), env["store"].get("111"))


# ------------------------------ agent tools ----------------------------------
def _iso(delta_days: float) -> str:
    return (datetime.now(WIB) + timedelta(days=delta_days)).isoformat(timespec="minutes")


def _task(title, deadline_days=None, created_days=-1, done=False, course="gc-c1"):
    deadline = _iso(deadline_days) if deadline_days is not None else None
    return {
        "course_id": course,
        "matkul": "Basis Data",
        "jenis": "tugas",
        "judul": title,
        "pertemuan": None,
        "deadline": deadline,
        "deadline_ts": int(datetime.fromisoformat(deadline).timestamp()) if deadline else None,
        "status_ringkas": "Sudah dikumpulkan" if done else "BELUM dikumpulkan",
        "url": "https://classroom/" + title,
        "sudah_dikumpulkan": done,
        "deskripsi": "x" * 900,
        "dibuat": _iso(created_days),
    }


@pytest.fixture
def agent_data(tmp_path, monkeypatch):
    usu = tmp_path / "assignments.json"
    usu.write_text(
        json.dumps(
            {
                "diperbarui": "2026-10-12T08:00+07:00",
                "tugas": [
                    {
                        "matkul": "Pemrograman Visual",
                        "jenis": "tugas",
                        "judul": "Praktik 4",
                        "pertemuan": 4,
                        "deadline": "2026-10-13T11:30+07:00",
                        "status_ringkas": "BELUM dikumpulkan",
                        "url": "https://kelas.usu",
                        "sudah_dikumpulkan": False,
                        "deskripsi": "Buat kalkulator",
                    },
                ],
            }
        )
    )
    folder = tmp_path / "classroom"
    folder.mkdir()
    mine = {
        "user_id": "default",
        "diperbarui": "2026-10-12T12:00+07:00",
        "kelas": [
            {
                "course_id": "gc-c1",
                "nama": "Basis Data",
                "bagian": "Kelas A",
                "alias": ["basis data", "basis data kelas a"],
            },
            {"course_id": "gc-old", "nama": "Kelas 2024", "bagian": None, "alias": ["kelas 2024"]},
        ],
        "tugas": [
            _task("Tugas lama", deadline_days=-400, created_days=-410),  # 2024: disembunyikan
            _task("Baru lewat", deadline_days=-5),
            _task("Tugas ERD", deadline_days=8),
            _task("Kuis", created_days=-2, done=True),  # tanpa deadline, baru
            _task("Catatan lama", created_days=-200),  # tanpa deadline, lama: disembunyikan
            _task("Tugas 2024", deadline_days=-420, created_days=-430, course="gc-old"),
        ],
        "materi": [
            {
                "course_id": "gc-c1",
                "matkul": "Basis Data",
                "jenis": "materi",
                "judul": "Slide Normalisasi",
                "deskripsi": "Bentuk normal 1NF sampai 3NF",
                "topik": "Pertemuan 2",
                "pertemuan": 2,
                "lampiran": [
                    {"jenis": "drive", "judul": "normalisasi.pdf", "url": "https://drive/d"}
                ],
                "url": "https://classroom/m1",
                "dibuat": _iso(-7),
            },
            {
                "course_id": "gc-c1",
                "matkul": "Basis Data",
                "jenis": "pengumuman",
                "judul": "Kelas pindah ke lab",
                "deskripsi": "Minggu depan di lab 2",
                "topik": None,
                "pertemuan": None,
                "lampiran": [],
                "url": "https://classroom/a1",
                "dibuat": _iso(-2),
            },
        ],
    }
    other = {
        **mine,
        "user_id": "google-222",
        "kelas": [{"course_id": "gc-x", "nama": "Rahasia", "alias": ["rahasia"]}],
        "tugas": [_task("Tugas orang lain", deadline_days=3, course="gc-x")],
        "materi": [],
    }
    (folder / "111.json").write_text(json.dumps(mine))
    (folder / "222.json").write_text(json.dumps(other))
    monkeypatch.setattr(tools, "ASSIGNMENTS_FILE", usu)
    monkeypatch.setattr(tools, "CLASSROOM_DIR", folder)
    monkeypatch.setattr(tools, "get_settings", lambda: replace(get_settings(), user_id="default"))
    monkeypatch.setattr(tools, "_catalog", lambda: [])
    return folder


def test_list_assignments_sends_only_relevant_classroom_tasks(agent_data):
    result = tools.list_assignments()
    titles = [t["judul"] for t in result["tugas"]]
    # USU dulu, lalu Classroom: mendatang, baru lewat, tanpa deadline yang baru
    assert titles == ["Praktik 4", "Tugas ERD", "Baru lewat", "Kuis"]
    assert "Tugas orang lain" not in titles
    assert "sumber" not in result["tugas"][0] and result["tugas"][1]["sumber"] == "Google Classroom"
    assert len(result["tugas"][1]["soal"]) == tools.CLASSROOM_TASK_CHARS  # soal dipersingkat
    assert result["tugas"][0]["soal"] == "Buat kalkulator"  # USU tidak berubah
    assert result["classroom_diperbarui"] == "2026-10-12T12:00+07:00"
    assert result["classroom_tidak_ditampilkan"].startswith("3 tugas Classroom lama")
    pending = tools.list_assignments(only_pending=True)
    assert [t["judul"] for t in pending["tugas"]] == ["Praktik 4", "Tugas ERD", "Baru lewat"]


def test_classroom_task_list_is_capped(agent_data):
    data = json.loads((agent_data / "111.json").read_text())
    data["tugas"] = [_task(f"T{i:02d}", deadline_days=1 + i) for i in range(40)]
    (agent_data / "111.json").write_text(json.dumps(data))
    result = tools.list_assignments()
    classroom = [t["judul"] for t in result["tugas"] if t.get("sumber")]
    assert classroom == [f"T{i:02d}" for i in range(tools.MAX_CLASSROOM_TASKS)]  # terdekat dulu
    assert result["classroom_tidak_ditampilkan"].startswith("15 ")
    assert len(json.dumps(result)) < 20_000  # tetap kecil untuk LLM


def test_usu_only_users_see_no_change(agent_data):
    for path in agent_data.glob("*.json"):
        path.unlink()
    result = tools.list_assignments()
    # `peringatan` ada karena `diperbarui` fixture memang sudah lama; yang penting tidak ada
    # satu pun kunci Classroom untuk pengguna tanpa akun Google.
    assert set(result) == {"diperbarui", "tugas", "peringatan"} and len(result["tugas"]) == 1
    assert [s["function"]["name"] for s in tools.tool_schemas()] == [
        s["function"]["name"] for s in tools.SCHEMAS
    ]
    assert "error" in tools.get_classroom_materials()
    assert tools.course_overview() == ""


def test_classroom_materials_tool(agent_data):
    newest = tools.get_classroom_materials()
    assert [m["judul"] for m in newest["hasil"]] == ["Kelas pindah ke lab", "Slide Normalisasi"]
    found = tools.get_classroom_materials(course="basis data", query="normalisasi 3NF")
    assert [m["judul"] for m in found["hasil"]] == ["Slide Normalisasi"]
    assert found["hasil"][0]["lampiran"] == [
        {"jenis": "drive", "judul": "normalisasi.pdf", "url": "https://drive/d"}
    ]
    assert [m["judul"] for m in tools.get_classroom_materials(meeting=2)["hasil"]] == [
        "Slide Normalisasi"
    ]
    missing = tools.get_classroom_materials(course="fisika")
    assert "tidak ditemukan" in missing["error"] and missing["pilihan"] == [
        "Basis Data",
        "Kelas 2024",
    ]
    assert (
        "Rahasia" not in tools.get_classroom_materials(course="rahasia")["pilihan"]
    )  # milik orang lain
    assert tools.TOOLS["get_classroom_materials"] is tools.get_classroom_materials


def test_prompt_lists_only_active_classroom_classes(agent_data):
    assert "get_classroom_materials" in [s["function"]["name"] for s in tools.tool_schemas()]
    overview = tools.course_overview().splitlines()
    assert overview == [
        "- Basis Data (Kelas A) (Google Classroom)",
        "Kelas Google Classroom: tugas lewat list_assignments, materi & pengumuman lewat "
        "get_classroom_materials; 1 kelas lama tidak dicantumkan.",
    ]
