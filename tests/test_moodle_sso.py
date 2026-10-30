import time
from datetime import datetime, timedelta

import pytest
import requests

from edupad.config import MOODLE_URL, WIB
from edupad.core import moodle
from edupad.errors import LoginRequired
from edupad.jobs import keepalive


class FakeResponse:
    def __init__(self, url, text="", status=200):
        self.url, self.text, self.status_code, self.headers = url, text, status, {}


def _client(token_expires: float | None, final_url: str, monkeypatch, tmp_path):
    from edupad.core import session

    cookies = [{"name": "MoodleSession", "value": "lama", "domain": "kelas.usu.ac.id", "path": "/"}]
    if token_expires:
        cookies.append(
            {
                "name": "ssotok",
                "value": "jwt",
                "domain": ".usu.ac.id",
                "path": "/",
                "expires": int(token_expires),
            }
        )
    path = tmp_path / "session.json"
    session.write_json(path, {"cookies": cookies})
    monkeypatch.setattr(moodle, "MOODLE_SESSION_FILE", path)

    client = moodle.MoodleClient.__new__(moodle.MoodleClient)
    client._sesskey = "lama"
    client.http = requests.Session()
    client.http.cookies.set("MoodleSession", "lama", domain="kelas.usu.ac.id", path="/")
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        if url.endswith("/auth/jwtsso/login.php"):
            client.http.cookies.set("MoodleSession", "baru", domain="kelas.usu.ac.id", path="/")
            return FakeResponse(final_url)
        return FakeResponse(f"{MOODLE_URL}/my/courses.php", text='{"sesskey":"abc123"}')

    client.http.get = fake_get
    return client, calls


def test_sso_relogin_creates_new_session_from_valid_token(monkeypatch, tmp_path):
    client, calls = _client(time.time() + 3600, f"{MOODLE_URL}/my/", monkeypatch, tmp_path)
    client.sso_relogin()
    assert calls[0].endswith("/auth/jwtsso/login.php")
    assert client.sesskey == "abc123"
    assert client.http.cookies.get("MoodleSession", domain="kelas.usu.ac.id") == "baru"


def test_sso_relogin_refuses_expired_or_missing_token(monkeypatch, tmp_path):
    for expires in (None, time.time() - 60):
        client, calls = _client(expires, f"{MOODLE_URL}/my/", monkeypatch, tmp_path)
        with pytest.raises(LoginRequired, match="tidak ada atau sudah habis"):
            client.sso_relogin()
        assert calls == []


def test_sso_relogin_detects_redirect_to_sso_login_form(monkeypatch, tmp_path):
    client, _ = _client(
        time.time() + 3600, "https://sso.usu.ac.id/auth/login?callback=x", monkeypatch, tmp_path
    )
    with pytest.raises(LoginRequired, match="ditolak"):
        client.sso_relogin()


def test_relogin_is_rate_limited(monkeypatch):
    state = {}
    monkeypatch.setattr(keepalive, "get_state", lambda service: dict(state))
    monkeypatch.setattr(keepalive, "update_state", lambda service, **f: state.update(f))
    attempts = []

    class Client:
        def sso_relogin(self):
            attempts.append(1)

    assert keepalive._try_sso_relogin(Client())
    assert not keepalive._try_sso_relogin(Client())  # masih dalam jeda 2 jam
    state["last_sso_relogin"] = (datetime.now(WIB) - timedelta(hours=3)).isoformat()
    assert keepalive._try_sso_relogin(Client())
    assert len(attempts) == 2
