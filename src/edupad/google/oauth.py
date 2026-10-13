"""OAuth 2.0 Google (authorization code + PKCE) untuk login web EduPad.

Alur di server: browser -> /auth/google/login -> Google -> /auth/google/callback.
Client secret dan refresh token hanya ada di server, tidak pernah dikirim ke browser.
`access_type=offline` memberi refresh token sehingga sinkronisasi Classroom terjadwal
berjalan tanpa pengguna login ulang.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import requests

from edupad.config import Settings
from edupad.core import http_pool

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
ISSUERS = {"https://accounts.google.com", "accounts.google.com"}
TIMEOUT = 20
CLOCK_SKEW = 300  # detik; toleransi selisih jam server dengan Google

IDENTITY_SCOPES = ("openid", "email", "profile")
CLASSROOM_COURSES = "https://www.googleapis.com/auth/classroom.courses.readonly"
CLASSROOM_COURSEWORK = "https://www.googleapis.com/auth/classroom.coursework.me.readonly"
CLASSROOM_MATERIALS = "https://www.googleapis.com/auth/classroom.courseworkmaterials.readonly"
CLASSROOM_ANNOUNCEMENTS = "https://www.googleapis.com/auth/classroom.announcements.readonly"
CLASSROOM_TOPICS = "https://www.googleapis.com/auth/classroom.topics.readonly"
# Semua hanya-baca: kelas, tugas & nilai milik sendiri, materi, pengumuman, topik.
CLASSROOM_SCOPES = (
    CLASSROOM_COURSES,
    CLASSROOM_COURSEWORK,
    CLASSROOM_MATERIALS,
    CLASSROOM_ANNOUNCEMENTS,
    CLASSROOM_TOPICS,
)
SCOPES = IDENTITY_SCOPES + CLASSROOM_SCOPES

_CLASSROOM = "https://www.googleapis.com/auth/classroom."
# Izin lain yang juga membuka endpoint yang sama: versi baca-tulis, dan nama lama
# "student-submissions" yang masih dipakai Google untuk izin yang diberikan sebelumnya
# (diminta coursework.me.readonly, tercatat student-submissions.me.readonly).
SCOPE_EQUIVALENTS = {
    CLASSROOM_COURSES: {CLASSROOM_COURSES, _CLASSROOM + "courses"},
    CLASSROOM_COURSEWORK: {
        CLASSROOM_COURSEWORK,
        _CLASSROOM + "coursework.me",
        _CLASSROOM + "student-submissions.me.readonly",
    },
    CLASSROOM_MATERIALS: {CLASSROOM_MATERIALS, _CLASSROOM + "courseworkmaterials"},
    CLASSROOM_ANNOUNCEMENTS: {CLASSROOM_ANNOUNCEMENTS, _CLASSROOM + "announcements"},
    CLASSROOM_TOPICS: {CLASSROOM_TOPICS, _CLASSROOM + "topics"},
}


def scope_granted(scopes: object, needed: str) -> bool:
    """True bila `needed` atau izin yang setara ada di daftar izin token."""
    return bool(SCOPE_EQUIVALENTS.get(needed, {needed}) & set(scopes or ()))


class GoogleAuthError(RuntimeError):
    """Login atau token Google gagal. `code` singkat dan aman ditampilkan di web."""

    def __init__(self, message: str, code: str = "google_error"):
        super().__init__(message)
        self.code = code


class ReauthRequired(GoogleAuthError):
    """Refresh token dicabut atau kedaluwarsa: pengguna harus login ulang di web."""


@dataclass(frozen=True)
class Client:
    client_id: str
    client_secret: str
    redirect_uri: str

    @classmethod
    def from_settings(cls, settings: Settings) -> Client | None:
        """None bila GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET belum diisi."""
        if not (settings.google_client_id and settings.google_client_secret):
            return None
        return cls(
            settings.google_client_id,
            settings.google_client_secret,
            f"{settings.public_url}/auth/google/callback",
        )


@dataclass(frozen=True)
class LoginRequest:
    """Satu percobaan login dari satu browser; disimpan server sampai callback datang."""

    state: str  # anti-CSRF, juga disimpan di cookie browser
    verifier: str  # PKCE
    nonce: str  # anti-replay ID token
    consent: bool  # paksa layar izin agar Google mengirim refresh token


@dataclass(frozen=True)
class Tokens:
    access_token: str
    expires_at: float  # epoch detik
    refresh_token: str | None
    scopes: frozenset[str]  # kosong bila Google tidak menyebutkan (respons refresh)
    id_token: str | None


def new_login(consent: bool = False) -> LoginRequest:
    return LoginRequest(
        state=secrets.token_urlsafe(32),
        verifier=secrets.token_urlsafe(64),  # 86 karakter; PKCE meminta 43-128
        nonce=secrets.token_urlsafe(16),
        consent=consent,
    )


def code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def authorization_url(client: Client, login: LoginRequest) -> str:
    params = {
        "client_id": client.client_id,
        "redirect_uri": client.redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        # Tanpa include_granted_scopes: token hanya membawa izin yang diminta di sini,
        # bukan izin lain yang pernah diberikan ke project Google Cloud yang sama.
        "state": login.state,
        "nonce": login.nonce,
        "code_challenge": code_challenge(login.verifier),
        "code_challenge_method": "S256",
        # Refresh token hanya dikirim saat layar izin tampil; selain itu cukup pilih akun.
        "prompt": "select_account consent" if login.consent else "select_account",
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def _token_request(data: dict[str, str]) -> Tokens:
    started = time.time()
    try:
        response = http_pool.post(TOKEN_URL, data=data, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise GoogleAuthError(f"Google tidak bisa dihubungi: {e}", "network") from e
    try:
        body = response.json()
    except ValueError:
        body = {}
    if not isinstance(body, dict):
        body = {}
    if not response.ok:
        error = str(body.get("error") or f"http_{response.status_code}")
        detail = body.get("error_description") or ""
        message = f"Google HTTP {response.status_code}: {error} {detail}".strip()
        if error == "invalid_grant":
            raise ReauthRequired(message, error)
        raise GoogleAuthError(message, error)
    if not body.get("access_token"):
        raise GoogleAuthError("jawaban token Google tanpa access_token", "bad_response")
    return Tokens(
        access_token=body["access_token"],
        expires_at=started + int(body.get("expires_in") or 3600),
        refresh_token=body.get("refresh_token"),
        scopes=frozenset(str(body.get("scope") or "").split()),
        id_token=body.get("id_token"),
    )


def exchange_code(client: Client, code: str, verifier: str) -> Tokens:
    return _token_request(
        {
            "code": code,
            "client_id": client.client_id,
            "client_secret": client.client_secret,
            "redirect_uri": client.redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": verifier,
        }
    )


def refresh(client: Client, refresh_token: str) -> Tokens:
    """Access token baru. ReauthRequired bila refresh token sudah tidak berlaku."""
    return _token_request(
        {
            "client_id": client.client_id,
            "client_secret": client.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
    )


def id_token_claims(
    id_token: str | None, client: Client, nonce: str, now: float | None = None
) -> dict:
    """Klaim ID token dari token endpoint, sesudah iss/aud/exp/nonce/email diperiksa.

    Tanda tangan tidak diperiksa: token diterima langsung dari Google lewat HTTPS dengan
    client secret, yang menurut dokumentasi OpenID Connect Google sudah menjamin keasliannya.
    Karena itu token ini tidak boleh diteruskan ke komponen lain sebagai bukti identitas.
    """
    try:
        payload = (id_token or "").split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except (IndexError, ValueError, binascii.Error) as e:
        raise GoogleAuthError("ID token Google tidak bisa dibaca", "bad_id_token") from e
    if not isinstance(claims, dict):
        raise GoogleAuthError("ID token Google tidak valid", "bad_id_token")
    now = time.time() if now is None else now
    problems = []
    if claims.get("iss") not in ISSUERS:
        problems.append("iss")
    if claims.get("aud") != client.client_id:
        problems.append("aud")
    if not isinstance(claims.get("exp"), (int, float)) or claims["exp"] < now - CLOCK_SKEW:
        problems.append("exp")
    if not hmac.compare_digest(str(claims.get("nonce") or ""), nonce):
        problems.append("nonce")
    if not claims.get("sub"):
        problems.append("sub")
    if not claims.get("email") or claims.get("email_verified") not in (True, "true"):
        problems.append("email")
    if problems:
        raise GoogleAuthError(f"ID token Google ditolak ({', '.join(problems)})", "bad_id_token")
    return claims
