import json
from datetime import datetime
from types import SimpleNamespace

import pytest
import requests

from edupad import cli
from edupad.collectors import attendance
from edupad.collectors.attendance import simplify_meeting
from edupad.config import SATU_URL, USU_LATITUDE, USU_LOCATION, USU_LONGITUDE, WIB
from edupad.errors import EXIT_LOGIN_REQUIRED, EXIT_OK, LoginRequired

NOW = datetime(2026, 10, 1, 15, 30, tzinfo=WIB)


def _meeting(**overrides) -> dict:
    meeting = {
        "id": "m1",
        "meeting_count": 7,
        "meeting_name": "Pertemuan 7",
        "meeting_date": "2026-10-01 15:20:00",
        "meeting_end_time": "2026-10-01 16:30:00",
        "realized_learning_material": "Sitasi",
        "active": False,
        "presence": None,
        "use_qr": True,
        "use_direct": True,
    }
    meeting.update(overrides)
    return meeting


def test_open_window_without_presence_needs_filling():
    m = simplify_meeting(_meeting(), NOW)
    assert m["perlu_diisi"] and m["cara"] == ["QR", "langsung"]


def test_active_flag_opens_presence_outside_window():
    assert simplify_meeting(_meeting(meeting_date=None, meeting_end_time=None, active=True), NOW)[
        "perlu_diisi"
    ]


def test_filled_presence_is_ignored():
    assert not simplify_meeting(_meeting(presence="hadir"), NOW)["perlu_diisi"]


def test_past_and_future_meetings_are_not_open():
    past = _meeting(meeting_date="2026-09-24 15:10:00", meeting_end_time="2026-09-24 16:00:00")
    future = _meeting(meeting_date=None, meeting_end_time=None)
    assert not simplify_meeting(past, NOW)["perlu_diisi"]
    assert not simplify_meeting(future, NOW)["perlu_diisi"]


class FakeServer:
    """Portal SATU palsu: GET presensi per kelas, POST presensi langsung."""

    def __init__(self, meetings, post_error=None, records_post=True):
        self.meetings = meetings
        self.post_error = post_error
        self.records_post = records_post
        self.posts = []

    def get_json(self, http, path, token=None):
        return {"data": {"presences": [{"class_meeting": [dict(m) for m in self.meetings]}]}}

    def post(self, url, files=None, **kwargs):
        form = {k: v for k, (_, v) in files.items()}
        self.posts.append((url, form))
        if isinstance(self.post_error, _Response):
            return self.post_error
        if self.post_error:
            raise self.post_error
        if self.records_post:
            for m in self.meetings:
                if m["id"] == form["class_meeting_id"]:
                    m["presence"] = "hadir"
        return _Response({"success": True})


class _Response:
    def __init__(self, body, status_code=200, text=""):
        self.body, self.status_code, self.text = body, status_code, text

    def raise_for_status(self):
        pass

    def json(self):
        return self.body


@pytest.fixture
def portal(monkeypatch, tmp_path):
    """Pasang FakeServer & catat notifikasi; kembalikan fungsi pembuat server."""
    sent, state = [], {}

    def make(*meetings, **kwargs):
        server = FakeServer([_meeting(**m) for m in meetings], **kwargs)
        http = SimpleNamespace(post=server.post)
        monkeypatch.setattr(attendance, "get_json", server.get_json)
        monkeypatch.setattr(attendance, "cookie_session", lambda _: http)
        server.sent, server.state = sent, state
        return server

    klass = {
        "matkul": "SPK",
        "kode": "TIF 3 001",
        "kelas": "B",
        "moodle_course_id": "1",
        "satu_class_id": "c1",
    }
    monkeypatch.setattr(attendance, "krs_classes", lambda: [klass])
    monkeypatch.setattr(attendance, "load_cookies", lambda _: {"cookies": [{}]})
    monkeypatch.setattr(
        attendance,
        "satu_session",
        lambda _: {"user": {"identity": "241712061"}, "accessToken": "t"},
    )
    monkeypatch.setattr(attendance, "persist_cookie_updates", lambda *a: None)
    monkeypatch.setattr(attendance, "report_login_ok", lambda _: None)
    monkeypatch.setattr(attendance, "get_state", lambda _: dict(state))
    monkeypatch.setattr(attendance, "update_state", lambda _, **f: state.update(f))
    monkeypatch.setattr(attendance, "notify", lambda msg: sent.append(msg) or True)
    monkeypatch.setattr(attendance, "ATTENDANCE_FILE", tmp_path / "attendance.json")
    monkeypatch.setattr(attendance, "FILL_FAILURE_LOG", tmp_path / "failures.jsonl")
    monkeypatch.setattr(attendance, "SATU_LOCK_FILE", tmp_path / "satu.lock")
    monkeypatch.setattr(attendance, "datetime", _FrozenDatetime)
    return make


class _FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW


def _written(tmp_path_file):
    return json.loads(tmp_path_file.read_text(encoding="utf-8"))


def test_monitor_notifies_open_meeting_only_once(portal):
    server = portal({})
    assert attendance.run() == EXIT_OK
    assert attendance.run() == EXIT_OK
    assert len(server.sent) == 1 and "Presensi dibuka" in server.sent[0]
    assert server.posts == []


def test_fill_posts_and_verifies_presence(portal):
    server = portal({})
    assert attendance.run(fill=True) == EXIT_OK
    assert server.posts == [
        (
            f"{SATU_URL}/app/proxy/study-card/presence",
            {
                "class_meeting_id": "m1",
                "class_id": "c1",
                "latitude": str(USU_LATITUDE),
                "longitude": str(USU_LONGITUDE),
                "location": USU_LOCATION,
                "nim": "241712061",
            },
        )
    ]
    assert len(server.sent) == 1 and server.sent[0].startswith("✅")
    saved = _written(attendance.ATTENDANCE_FILE)["mata_kuliah"][0]["pertemuan"][0]
    assert saved["status"] == "hadir" and not saved["perlu_diisi"]


def test_fill_accepted_but_not_recorded_is_reported_as_failure(portal):
    server = portal({}, records_post=False)
    assert attendance.run(fill=True) == EXIT_OK
    assert len(server.sent) == 1
    assert "Presensi dibuka" in server.sent[0] and "Gagal diisi otomatis" in server.sent[0]
    # run berikutnya mencoba lagi tanpa mengirim notifikasi ulang
    attendance.run(fill=True)
    assert len(server.posts) == 2 and len(server.sent) == 1


@pytest.mark.parametrize(
    "error",
    [requests.ConnectionError("putus"), ValueError("bukan JSON"), LoginRequired("HTTP 401")],
)
def test_fill_error_does_not_crash(portal, error):
    server = portal({}, post_error=error)
    assert attendance.run(fill=True) == EXIT_OK
    assert "Gagal diisi otomatis" in server.sent[0]


def test_qr_only_meeting_is_notified_not_posted(portal):
    server = portal({"use_direct": False})
    attendance.run(fill=True)
    attendance.run(fill=True)
    assert server.posts == []
    assert len(server.sent) == 1 and "Cara: QR" in server.sent[0]


def test_dry_run_neither_posts_nor_notifies(portal):
    server = portal({})
    assert attendance.run(fill=True, dry_run=True) == EXIT_OK
    assert server.posts == [] and server.sent == [] and server.state == {}


def test_closed_meeting_is_left_alone(portal):
    server = portal(
        {"presence": "hadir"}, {"id": "m2", "meeting_date": None, "meeting_end_time": None}
    )
    attendance.run(fill=True)
    assert server.posts == [] and server.sent == []


def test_expired_session_returns_login_required(portal, monkeypatch):
    portal({})
    expired = []

    def raise_login(_):
        raise LoginRequired("sesi SATU berakhir")

    monkeypatch.setattr(attendance, "satu_session", raise_login)
    monkeypatch.setattr(attendance, "report_login_expired", lambda *a: expired.append(a))
    assert attendance.run(fill=True) == EXIT_LOGIN_REQUIRED
    assert expired


def test_cli_routes_fill_flags(monkeypatch):
    calls = []
    monkeypatch.setattr(attendance, "run", lambda **kw: calls.append(kw) or 0)
    monkeypatch.setattr(cli, "setup_logging", lambda _: None)
    cli.main(["attendance"])
    cli.main(["attendance", "--fill"])
    cli.main(["attendance", "--dry-run"])
    assert calls == [
        {"fill": False, "dry_run": False},
        {"fill": True, "dry_run": False},
        {"fill": True, "dry_run": True},
    ]


def _failures():
    lines = attendance.FILL_FAILURE_LOG.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines]


def test_failed_fill_is_logged_with_server_response(portal):
    portal({}, post_error=_Response(None, status_code=422, text='{"message":"di luar lokasi"}'))
    attendance.run(fill=True)
    [entry] = _failures()
    assert entry["id"] == "m1" and entry["status"] == "error"
    assert "HTTP 422" in entry["error"] and "di luar lokasi" in entry["error"]


def test_unverified_fill_is_logged_with_response(portal):
    portal({}, records_post=False)
    attendance.run(fill=True)
    [entry] = _failures()
    assert entry["response"] == {"success": True} and "masih kosong" in entry["error"]


def test_qr_only_is_logged_and_success_is_not(portal):
    portal({"use_direct": False}, {"id": "m2"})
    attendance.run(fill=True)
    assert [(e["id"], e["error"]) for e in _failures()] == [("m1", "hanya bisa lewat QR")]


def test_monitor_only_writes_no_failure_log(portal):
    portal({})
    attendance.run()
    assert not attendance.FILL_FAILURE_LOG.exists()
