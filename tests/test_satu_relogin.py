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
