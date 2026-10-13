import base64
import hashlib
import json
import time
from dataclasses import replace
from urllib.parse import parse_qs, urlsplit

import pytest

from edupad.config import get_settings
from edupad.google import oauth
from edupad.google.accounts import AccountStore, SessionStore, edupad_user_id, has_classroom

CLIENT = oauth.Client(
    "client-123.apps.googleusercontent.com", "secret", "http://localhost:5173/auth/google/callback"
)


def id_token(**claims) -> str:
    base = {
        "iss": "https://accounts.google.com",
        "aud": CLIENT.client_id,
        "exp": time.time() + 3600,
        "nonce": "n-1",
        "sub": "111",
        "email": "siswa@gmail.com",
        "email_verified": True,
        "name": "Siti Aminah",
    }
    payload = base64.urlsafe_b64encode(json.dumps({**base, **claims}).encode()).rstrip(b"=")
    return f"header.{payload.decode()}.signature"


class FakeResponse:
    def __init__(self, status=200, body=None):
        self.status_code, self.ok, self._body = status, status < 400, body or {}

    def json(self):
        if self._body is ValueError:
            raise ValueError("bukan JSON")
        return self._body


def test_client_from_settings_builds_redirect_uri():
    settings = replace(get_settings(), google_client_id=None, google_client_secret=None)
    assert oauth.Client.from_settings(settings) is None
    settings = replace(
        settings, google_client_id="id", google_client_secret="s", public_url="https://edupad.id"
    )
    assert (
        oauth.Client.from_settings(settings).redirect_uri
        == "https://edupad.id/auth/google/callback"
    )


def test_authorization_url_requests_offline_classroom_access_with_pkce():
    login = oauth.new_login()
    url = urlsplit(oauth.authorization_url(CLIENT, login))
    params = {k: v[0] for k, v in parse_qs(url.query).items()}
    assert f"{url.scheme}://{url.netloc}{url.path}" == oauth.AUTH_URL
    assert params["client_id"] == CLIENT.client_id and params["redirect_uri"] == CLIENT.redirect_uri
    assert params["response_type"] == "code" and params["access_type"] == "offline"
    assert params["state"] == login.state and params["nonce"] == login.nonce
    assert params["prompt"] == "select_account"
    assert "include_granted_scopes" not in params  # tidak mewarisi izin aplikasi lain
    expected = base64.urlsafe_b64encode(hashlib.sha256(login.verifier.encode()).digest()).rstrip(
        b"="
    )
    assert (
        params["code_challenge"] == expected.decode() and params["code_challenge_method"] == "S256"
    )
    scopes = params["scope"].split()
    assert {"openid", "email", "profile", *oauth.CLASSROOM_SCOPES} == set(scopes)
    assert all(s.endswith(".readonly") for s in oauth.CLASSROOM_SCOPES)  # tidak pernah menulis
    assert 43 <= len(login.verifier) <= 128
    consent = parse_qs(
        urlsplit(oauth.authorization_url(CLIENT, oauth.new_login(consent=True))).query
    )
    assert consent["prompt"] == ["select_account consent"]


def test_exchange_code_sends_verifier_and_parses_tokens(monkeypatch):
    sent = []
    body = {
        "access_token": "at",
        "expires_in": 3599,
        "refresh_token": "rt",
        "scope": "openid email",
        "id_token": "x.y.z",
    }
    monkeypatch.setattr(
        oauth.http_pool, "post", lambda url, **kw: sent.append((url, kw)) or FakeResponse(body=body)
    )
    tokens = oauth.exchange_code(CLIENT, "kode", "verifier")
    url, kw = sent[0]
    assert url == oauth.TOKEN_URL
    assert kw["data"] == {
        "code": "kode",
        "client_id": CLIENT.client_id,
        "client_secret": "secret",
        "redirect_uri": CLIENT.redirect_uri,
        "grant_type": "authorization_code",
        "code_verifier": "verifier",
    }
    assert (tokens.access_token, tokens.refresh_token, tokens.id_token) == ("at", "rt", "x.y.z")
    assert tokens.scopes == {"openid", "email"} and tokens.expires_at > time.time() + 3500


def test_token_errors(monkeypatch):
    monkeypatch.setattr(
        oauth.http_pool, "post", lambda url, **kw: FakeResponse(400, {"error": "invalid_grant"})
    )
    with pytest.raises(oauth.ReauthRequired):
        oauth.refresh(CLIENT, "rt")
    monkeypatch.setattr(
        oauth.http_pool, "post", lambda url, **kw: FakeResponse(401, {"error": "invalid_client"})
    )
    with pytest.raises(oauth.GoogleAuthError) as e:
        oauth.refresh(CLIENT, "rt")
    assert e.value.code == "invalid_client" and not isinstance(e.value, oauth.ReauthRequired)
    monkeypatch.setattr(oauth.http_pool, "post", lambda url, **kw: FakeResponse(500, ValueError))
    with pytest.raises(oauth.GoogleAuthError, match="500"):
        oauth.refresh(CLIENT, "rt")
    monkeypatch.setattr(
        oauth.http_pool, "post", lambda url, **kw: FakeResponse(200, {"token_type": "Bearer"})
    )
    with pytest.raises(oauth.GoogleAuthError, match="access_token"):
        oauth.refresh(CLIENT, "rt")

    def offline(url, **kw):
        raise oauth.requests.ConnectionError("tidak ada jaringan")

    monkeypatch.setattr(oauth.http_pool, "post", offline)
    with pytest.raises(oauth.GoogleAuthError) as e:
        oauth.refresh(CLIENT, "rt")
    assert e.value.code == "network"


def test_id_token_claims_are_validated():
    assert oauth.id_token_claims(id_token(), CLIENT, "n-1")["email"] == "siswa@gmail.com"
    assert oauth.id_token_claims(id_token(iss="accounts.google.com"), CLIENT, "n-1")
    assert oauth.id_token_claims(id_token(email_verified="true"), CLIENT, "n-1")
    bad = [
        id_token(iss="https://evil.example"),
        id_token(aud="aplikasi-lain"),
        id_token(exp=time.time() - 3600),
        id_token(nonce="n-lain"),
        id_token(email_verified=False),
        id_token(sub=""),
        "bukan-jwt",
        "a.!!!.c",
        None,
    ]
    for token in bad:
        with pytest.raises(oauth.GoogleAuthError):
            oauth.id_token_claims(token, CLIENT, "n-1")


def tokens(**kw):
    base = {
        "access_token": "at",
        "expires_at": time.time() + 3600,
        "refresh_token": "rt",
        "scopes": frozenset({"openid", oauth.CLASSROOM_COURSES}),
        "id_token": None,
    }
    return oauth.Tokens(**{**base, **kw})


CLAIMS = {
    "sub": "111",
    "email": "siswa@gmail.com",
    "name": "Siti",
    "picture": "https://lh3.googleusercontent.com/a",
}


def test_account_store_keeps_refresh_token_across_logins(tmp_path):
    store = AccountStore(tmp_path / "accounts.json", tmp_path / "lock")
    first = store.save_login(CLAIMS, tokens(), "default")
    assert has_classroom(first) and first["refresh_token"] == "rt"
    second = store.save_login(CLAIMS, tokens(refresh_token=None, access_token="at2"), "default")
    assert (
        second["refresh_token"] == "rt" and second["access_token"] == "at2"
    )  # Google tak kirim lagi
    assert second["created_at"] == first["created_at"]
    assert (tmp_path / "accounts.json").stat().st_mode & 0o777 == 0o600


def test_access_token_refreshes_and_marks_revoked_accounts(tmp_path, monkeypatch):
    store = AccountStore(tmp_path / "accounts.json", tmp_path / "lock")
    store.save_login(CLAIMS, tokens(expires_at=time.time() + 30), "default")  # hampir habis
    refreshed = []

    def refresh(client, refresh_token):
        refreshed.append(refresh_token)
        return tokens(access_token="baru", refresh_token=None, scopes=frozenset())

    monkeypatch.setattr(oauth, "refresh", refresh)
    assert store.access_token("111", CLIENT) == "baru" and refreshed == ["rt"]
    assert store.access_token("111", CLIENT) == "baru" and refreshed == ["rt"]  # masih berlaku
    saved = store.get("111")
    assert saved["refresh_token"] == "rt" and oauth.CLASSROOM_COURSES in saved["scopes"]

    def revoked(client, refresh_token):
        raise oauth.ReauthRequired("Google HTTP 400: invalid_grant", "invalid_grant")

    monkeypatch.setattr(oauth, "refresh", revoked)
    with pytest.raises(oauth.ReauthRequired):
        store.access_token("111", CLIENT, now=lambda: time.time() + 7200)
    assert store.get("111")["status"] == "reauth_required"  # tersimpan walau error dilempar
    with pytest.raises(oauth.ReauthRequired):
        store.access_token("111", CLIENT)  # tidak mencoba refresh token yang sudah ditolak
    with pytest.raises(oauth.GoogleAuthError):
        store.access_token("tidak-ada", CLIENT)
    store.save_login(CLAIMS, tokens(), "default")  # login ulang memulihkan akun
    assert store.get("111")["status"] == "ok"


def test_sessions_store_only_hashes_and_expire(tmp_path):
    sessions = SessionStore(tmp_path / "sessions.json", tmp_path / "lock", lifetime=60)
    token = sessions.create("111")
    assert (
        sessions.get(token) == "111"
        and sessions.get("palsu") is None
        and sessions.get(None) is None
    )
    assert token not in (tmp_path / "sessions.json").read_text()
    sessions.delete(token)
    assert sessions.get(token) is None
    expired = SessionStore(tmp_path / "sessions.json", tmp_path / "lock", lifetime=-1)
    assert expired.get(expired.create("111")) is None


def test_owner_emails_map_to_the_agent_user():
    settings = replace(
        get_settings(), user_id="default", owner_emails=frozenset({"pemilik@gmail.com"})
    )
    assert edupad_user_id("Pemilik@Gmail.com", "1", settings) == "default"
    assert edupad_user_id("orang@gmail.com", "2", settings) == "google-2"


def test_rejected_refresh_token_is_never_reused(tmp_path, monkeypatch):
    store = AccountStore(tmp_path / "accounts.json", tmp_path / "lock")
    store.save_login(CLAIMS, tokens(expires_at=0), "default")

    def revoked(client, refresh_token):
        raise oauth.ReauthRequired("invalid_grant", "invalid_grant")

    monkeypatch.setattr(oauth, "refresh", revoked)
    with pytest.raises(oauth.ReauthRequired):
        store.access_token("111", CLIENT)
    # login ulang tanpa refresh token baru: token mati tidak boleh dibawa lagi
    account = store.save_login(CLAIMS, tokens(refresh_token=None), "default")
    assert account["refresh_token"] is None and account["status"] == "ok"


def test_equivalent_and_legacy_scope_names_count_as_granted():
    legacy = [
        "openid",
        oauth._CLASSROOM + "courses",
        oauth._CLASSROOM + "student-submissions.me.readonly",
    ]
    assert oauth.scope_granted(legacy, oauth.CLASSROOM_COURSEWORK)  # nama lama dari Google
    assert oauth.scope_granted(legacy, oauth.CLASSROOM_COURSES)  # versi baca-tulis mencakup baca
    assert not oauth.scope_granted(legacy, oauth.CLASSROOM_MATERIALS)
    assert not oauth.scope_granted(None, oauth.CLASSROOM_COURSES)
    assert has_classroom({"scopes": legacy}) and not has_classroom({"scopes": ["openid"]})
