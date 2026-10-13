"""Alur web lewat server sungguhan; hanya token endpoint Google yang ditiru."""

import base64
import hashlib
import http.client
import json
import logging
import threading
import time
from dataclasses import replace
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest

from edupad import server as srv
from edupad.config import get_settings
from edupad.google import oauth
from edupad.google.accounts import AccountStore, SessionStore
from edupad.webapp import WebApp

CLIENT_ID = "client-123.apps.googleusercontent.com"


class StubAgent:
    def close(self):
        pass


def make_id_token(expected_nonce: str, **claims) -> str:
    payload = {
        "iss": "https://accounts.google.com",
        "aud": CLIENT_ID,
        "exp": time.time() + 3600,
        "nonce": expected_nonce,  # claims boleh menimpanya (uji replay)
        "sub": "111",
        "email": "siswa@gmail.com",
        "email_verified": True,
        "name": "Siti Aminah",
        "picture": "https://lh3.googleusercontent.com/a/foto",
        **claims,
    }
    return (
        "h." + base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode() + ".s"
    )


class FakeTokenResponse:
    def __init__(self, status, body):
        self.status_code, self.ok, self._body = status, status < 400, body

    def json(self):
        return self._body


@pytest.fixture
def site(tmp_path, monkeypatch):
    settings = replace(
        get_settings(),
        google_client_id=CLIENT_ID,
        google_client_secret="rahasia",
        public_url="http://localhost:5173",
        user_id="default",
        owner_emails=frozenset({"siswa@gmail.com"}),
    )
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>EduPad</title>")
    (dist / "assets" / "app-123.js").write_text("console.log('edupad')")
    (tmp_path / "rahasia.txt").write_text("jangan bocor")
    synced = []
    state = SimpleNamespace(settings=settings, synced=synced, token_calls=[], token_response=None)
    web = WebApp(
        settings=lambda: state.settings,
        accounts=AccountStore(tmp_path / "accounts.json", tmp_path / "lock"),
        sessions=SessionStore(tmp_path / "sessions.json", tmp_path / "lock"),
        dist_dir=dist,
        classroom_dir=tmp_path / "classroom",
        on_login=synced.append,
    )

    def fake_post(url, **kwargs):
        state.token_calls.append((url, kwargs))
        status, body = state.token_response(kwargs["data"])
        return FakeTokenResponse(status, body)

    monkeypatch.setattr(oauth.http_pool, "post", fake_post)
    server = srv.EduPadServer(("127.0.0.1", 0), "token-perangkat", agent=StubAgent(), web=web)
    threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True
    ).start()
    state.server, state.web, state.tmp = server, web, tmp_path
    yield state
    server.shutdown()
    server.server_close()


def request(site, method, path, cookies=None, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", site.server.server_address[1], timeout=5)
    all_headers = dict(headers or {})
    if cookies:
        all_headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in cookies.items())
    conn.request(method, path, headers=all_headers)
    response = conn.getresponse()
    body = response.read()
    conn.close()
    response.cookies = {c.split("=", 1)[0]: c for c in response.headers.get_all("Set-Cookie") or []}
    return response, body


def cookie_value(set_cookie: str) -> str:
    return set_cookie.split(";", 1)[0].split("=", 1)[1]


def start_login(site, path="/auth/google/login"):
    response, _ = request(site, "GET", path)
    assert response.status == 302
    params = {k: v[0] for k, v in parse_qs(urlsplit(response.getheader("Location")).query).items()}
    return params, {"edupad_login": cookie_value(response.cookies["edupad_login"])}


def google_returns(site, refresh_token="rt", scopes=None, **claims):
    def respond(data):
        nonce = site.last_nonce
        body = {
            "access_token": "at",
            "expires_in": 3599,
            "id_token": make_id_token(nonce, **claims),
            "scope": " ".join(scopes if scopes is not None else oauth.SCOPES),
        }
        if refresh_token:
            body["refresh_token"] = refresh_token
        return 200, body

    site.token_response = respond


def login(site, **google):
    params, cookies = start_login(site)
    site.last_nonce = params["nonce"]
    google_returns(site, **google)
    return request(
        site, "GET", f"/auth/google/callback?state={params['state']}&code=kode-1", cookies
    )


def test_login_redirects_to_google_with_browser_bound_state(site):
    response, _ = request(site, "GET", "/auth/google/login")
    location = urlsplit(response.getheader("Location"))
    params = parse_qs(location.query)
    assert (
        response.status == 302
        and f"{location.scheme}://{location.netloc}{location.path}" == oauth.AUTH_URL
    )
    assert params["redirect_uri"] == ["http://localhost:5173/auth/google/callback"]
    cookie = response.cookies["edupad_login"]
    assert cookie_value(cookie) == params["state"][0]
    assert "Path=/auth/google" in cookie and "HttpOnly" in cookie and "SameSite=Lax" in cookie
    assert "Secure" not in cookie  # http://localhost
    assert response.getheader("Cache-Control") == "no-store"


def test_full_login_reaches_dashboard_and_api(site):
    params, cookies = start_login(site)
    site.last_nonce = params["nonce"]
    google_returns(site)
    response, _ = request(
        site, "GET", f"/auth/google/callback?state={params['state']}&code=kode-1", cookies
    )
    assert response.status == 302 and response.getheader("Location") == "/dashboard"
    session = response.cookies["edupad_session"]
    assert "HttpOnly" in session and "Max-Age=2592000" in session
    assert "Max-Age=0" in response.cookies["edupad_login"]  # state sekali pakai dihapus

    url, kwargs = site.token_calls[0]
    assert url == oauth.TOKEN_URL and kwargs["data"]["code"] == "kode-1"
    verifier = kwargs["data"]["code_verifier"]
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    )
    assert challenge == params["code_challenge"]  # PKCE cocok dengan URL login

    response, body = request(site, "GET", "/api/me", {"edupad_session": cookie_value(session)})
    me = json.loads(body)
    assert (
        response.status == 200 and me["email"] == "siswa@gmail.com" and me["name"] == "Siti Aminah"
    )
    assert me["classroom"] == {
        "granted": True,
        "reauth_required": False,
        "courses": None,
        "synced_at": None,
    }
    account = site.web.accounts.get("111")
    assert account["refresh_token"] == "rt" and account["user_id"] == "default"  # email pemilik
    assert site.synced == ["siswa@gmail.com"]  # sinkronisasi Classroom pertama dimulai


def test_other_users_get_their_own_space_and_partial_consent_is_reported(site):
    response, _ = login(
        site, email="teman@gmail.com", sub="222", scopes=["openid", "email", "profile"]
    )
    session = cookie_value(response.cookies["edupad_session"])
    me = json.loads(request(site, "GET", "/api/me", {"edupad_session": session})[1])
    assert me["classroom"]["granted"] is False
    assert site.web.accounts.get("222")["user_id"] == "google-222"
    assert site.synced == []  # tanpa izin Classroom tidak ada sinkronisasi


def test_callback_rejects_forged_or_reused_state(site):
    params, cookies = start_login(site)
    site.last_nonce = params["nonce"]
    google_returns(site)
    callback = f"/auth/google/callback?state={params['state']}&code=kode-1"
    for jar in ({}, {"edupad_login": "state-lain"}):
        response, _ = request(site, "GET", callback, jar)
        assert response.getheader("Location") == "/?error=state"
    response, _ = request(site, "GET", callback, cookies)  # state sudah terpakai di atas
    assert response.getheader("Location") == "/?error=state"
    assert site.token_calls == [] and "edupad_session" not in response.cookies


def test_google_errors_return_to_landing_with_a_code(site):
    response, _ = request(site, "GET", "/auth/google/callback?error=access_denied&state=x")
    assert response.getheader("Location") == "/?error=access_denied"
    params, cookies = start_login(site)
    site.token_response = lambda data: (400, {"error": "invalid_grant"})
    response, _ = request(
        site, "GET", f"/auth/google/callback?state={params['state']}&code=k", cookies
    )
    assert response.getheader("Location") == "/?error=google_error"
    response, _ = login(site, nonce="nonce-palsu")  # ID token replay
    assert response.getheader("Location") == "/?error=google_error"
    assert site.web.accounts.get("111") is None


def test_missing_refresh_token_asks_for_consent_once(site):
    response, _ = login(site, refresh_token=None)
    assert response.getheader("Location") == "/auth/google/login?consent=1"
    assert site.web.accounts.get("111") is None
    params, cookies = start_login(site, "/auth/google/login?consent=1")
    assert params["prompt"] == "select_account consent"
    site.last_nonce = params["nonce"]
    google_returns(site, refresh_token=None)
    response, _ = request(
        site, "GET", f"/auth/google/callback?state={params['state']}&code=k", cookies
    )
    assert response.getheader("Location") == "/dashboard"  # tidak berputar terus


def test_not_configured_login_explains_on_landing(site):
    site.settings = replace(site.settings, google_client_id=None)
    response, _ = request(site, "GET", "/auth/google/login")
    assert response.getheader("Location") == "/?error=not_configured"


def test_me_and_logout(site):
    assert request(site, "GET", "/api/me")[0].status == 401
    assert request(site, "GET", "/api/me", {"edupad_session": "palsu"})[0].status == 401
    session = cookie_value(login(site)[0].cookies["edupad_session"])
    jar = {"edupad_session": session}
    response, _ = request(
        site, "POST", "/auth/logout", jar, {"Origin": "https://situs-jahat.example"}
    )
    assert response.status == 403 and request(site, "GET", "/api/me", jar)[0].status == 200
    response, _ = request(site, "POST", "/auth/logout", jar, {"Origin": "http://localhost:5173"})
    assert response.status == 200 and "Max-Age=0" in response.cookies["edupad_session"]
    assert request(site, "GET", "/api/me", jar)[0].status == 401
    assert site.web.accounts.get("111")["refresh_token"] == "rt"  # sinkronisasi tetap bisa


def test_https_public_url_sets_secure_cookies(site):
    site.settings = replace(site.settings, public_url="https://edupad.example")
    response, _ = request(site, "GET", "/auth/google/login")
    assert "Secure" in response.cookies["edupad_login"]


def test_static_files_spa_fallback_and_traversal(site, tmp_path):
    response, body = request(site, "GET", "/")
    assert response.status == 200 and b"EduPad" in body
    assert response.getheader("Content-Type") == "text/html; charset=utf-8"
    assert "frame-ancestors 'none'" in response.getheader("Content-Security-Policy")
    assert response.getheader("Cache-Control") == "no-cache"
    assert request(site, "GET", "/dashboard")[1] == body
    response, js = request(site, "GET", "/assets/app-123.js")
    assert js == b"console.log('edupad')" and "immutable" in response.getheader("Cache-Control")
    assert response.getheader("X-Content-Type-Options") == "nosniff"
    for path in (
        "/assets/hilang.js",
        "/../rahasia.txt",
        "/%2e%2e/rahasia.txt",
        "/assets/..%2f..%2frahasia.txt",
    ):
        response, body = request(site, "GET", path)
        assert response.status == 404 and b"jangan bocor" not in body, path
    assert request(site, "GET", "/api/tidak-ada")[0].status == 404
    assert request(site, "POST", "/api/me")[0].status == 405
    (tmp_path / "dist" / "index.html").unlink()
    response, body = request(site, "GET", "/")
    assert response.status == 503 and b"npm run build" in body


def test_device_api_is_unchanged(site):
    response, body = request(site, "GET", "/v1/health")
    assert response.status == 200 and json.loads(body) == {"status": "ok"}
    response, body = request(site, "GET", "/v1/audio/apa")
    assert response.status == 401 and json.loads(body)["screen"]["lines"]  # tetap butuh token


def test_authorization_code_is_not_logged(site, caplog):
    with caplog.at_level(logging.INFO, logger="edupad.server"):
        login(site)
        time.sleep(0.05)
    assert "kode-1" not in caplog.text and "/auth/google/callback" in caplog.text


def test_expired_grant_asks_for_consent_again(site):
    login(site)  # refresh token "rt"
    accounts = site.web.accounts
    with open(accounts.path) as f:
        data = json.load(f)
    data["111"]["status"] = "reauth_required"  # mis. 7 hari di status Testing
    accounts.path.write_text(json.dumps(data))
    response, _ = login(site, refresh_token=None)  # Google tidak mengirim token baru
    assert response.getheader("Location") == "/auth/google/login?consent=1"
    params, cookies = start_login(site, "/auth/google/login?consent=1")
    site.last_nonce = params["nonce"]
    google_returns(site, refresh_token="rt-baru")
    response, _ = request(
        site, "GET", f"/auth/google/callback?state={params['state']}&code=k", cookies
    )
    assert response.getheader("Location") == "/dashboard"
    account = accounts.get("111")
    assert account["refresh_token"] == "rt-baru" and account["status"] == "ok"


def test_head_is_answered_for_pages_but_not_for_login_or_audio(site):
    conn = http.client.HTTPConnection("127.0.0.1", site.server.server_address[1], timeout=5)
    conn.request("GET", "/")
    page = conn.getresponse().read()
    conn.request("HEAD", "/")
    head = conn.getresponse()
    assert head.status == 200 and head.read() == b""
    assert head.getheader("Content-Length") == str(len(page))
    conn.request("GET", "/assets/app-123.js")  # koneksi yang sama tetap normal
    assert conn.getresponse().read() == b"console.log('edupad')"
    conn.close()
    assert request(site, "HEAD", "/v1/health")[0].status == 200
    params, cookies = start_login(site)
    callback = f"/auth/google/callback?state={params['state']}&code=k"
    assert request(site, "HEAD", callback, cookies)[0].status == 405
    assert request(site, "HEAD", "/v1/audio/apa")[0].status == 405
    assert request(site, "HEAD", "/api/me")[0].status == 405
    site.last_nonce = params["nonce"]
    google_returns(site)
    response, _ = request(site, "GET", callback, cookies)  # HEAD tidak menghabiskan state login
    assert response.getheader("Location") == "/dashboard"
