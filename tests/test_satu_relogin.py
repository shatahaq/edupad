import pytest

from edupad.collectors import schedule
from edupad.config import SATU_URL
from edupad.errors import LoginRequired

AUTH_URL = "https://id.usu.ac.id/realms/usu/protocol/openid-connect/auth?client_id=satu"


class FakeResponse:
    def __init__(self, url="", status=200, json=None, headers=None):
        self.url, self.status_code, self._json = url, status, json
        self.headers = headers or {"content-type": "application/json"}

    def json(self):
        return self._json

    def raise_for_status(self):
        pass


class FakeHttp:
    def __init__(self, final_url):
        self.final_url = final_url
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(("GET", url))
        if url.endswith("/app/auth/csrf"):
            return FakeResponse(json={"csrfToken": "abc"})
        if url.endswith("/app/auth/session"):
            return FakeResponse(json={"user": {"identity": "241712061"}, "accessToken": "t"})
        return FakeResponse(url=self.final_url, headers={"content-type": "text/html"})

    def post(self, url, data=None, **kwargs):
        self.calls.append(("POST", url))
        assert data["csrfToken"] == "abc"
        return FakeResponse(json={"url": AUTH_URL})


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(schedule.time, "sleep", lambda _: None)


def test_silent_relogin_goes_through_keycloak():
    http = FakeHttp(final_url=f"{SATU_URL}/home")
    session = schedule.silent_relogin(http)
    assert session["user"]["identity"] == "241712061"
    assert ("GET", AUTH_URL) in http.calls


def test_silent_relogin_detects_expired_sso():
    http = FakeHttp(final_url="https://id.usu.ac.id/realms/usu/login-actions/authenticate")
    with pytest.raises(LoginRequired):
        schedule.silent_relogin(http)


SESSION = {"user": {"identity": "241712061"}, "accessToken": "t"}


def test_with_relogin_uses_current_session_when_valid(monkeypatch):
    monkeypatch.setattr(schedule, "satu_session", lambda _: SESSION)
    monkeypatch.setattr(schedule, "silent_relogin", lambda _: pytest.fail("tidak perlu login"))
    assert schedule.with_relogin(object(), lambda s: s["accessToken"]) == "t"


@pytest.fixture
def satu_keepalive(monkeypatch, tmp_path):
    """keepalive SATU dengan status & cookie palsu; kembalikan catatan pemanggilan."""
    from edupad.jobs import keepalive

    calls = {"ok": 0, "expired": 0}
    state = {}
    monkeypatch.setattr(keepalive, "SATU_LOCK_FILE", tmp_path / "satu.lock")
    monkeypatch.setattr(keepalive, "load_cookies", lambda _: {"cookies": [{}], "login_at": None})
    monkeypatch.setattr(keepalive, "get_state", lambda _: state)
    monkeypatch.setattr(keepalive, "cookie_session", lambda _: object())
    monkeypatch.setattr(keepalive, "persist_cookie_updates", lambda *a: None)
    monkeypatch.setattr(keepalive, "report_login_ok", lambda _: calls.update(ok=calls["ok"] + 1))
    monkeypatch.setattr(
        keepalive, "report_login_expired", lambda *a: calls.update(expired=calls["expired"] + 1)
    )
    return keepalive, state, calls


def test_keepalive_recovers_session_marked_expired(satu_keepalive, monkeypatch):
    """Job lain menandai habis di batas 8 jam; cookie SSO masih berlaku -> pulih sendiri."""
    keepalive, state, calls = satu_keepalive
    state["expired_since"] = "2026-10-15T09:00:05+07:00"
    monkeypatch.setattr(schedule, "silent_relogin", lambda _: SESSION)
    assert keepalive.keep_satu_alive() == 0
    assert calls == {"ok": 1, "expired": 0}


def test_keepalive_reports_dead_sso_once(satu_keepalive, monkeypatch):
    keepalive, state, calls = satu_keepalive

    def dead(_):
        raise LoginRequired("sesi SSO Keycloak berakhir")

    monkeypatch.setattr(schedule, "silent_relogin", dead)
    assert keepalive.keep_satu_alive() != 0
    state["expired_since"] = "2026-10-17T10:00:00+07:00"  # dicatat report_login_expired
    assert keepalive.keep_satu_alive() != 0
    assert calls == {"ok": 0, "expired": 1}
