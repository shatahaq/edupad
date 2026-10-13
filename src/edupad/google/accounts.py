"""Akun Google yang login di web EduPad, dan sesi browser-nya.

Disimpan di user_data/google/ (0600, tidak di-commit) karena refresh token memberi akses
baca Classroom tanpa pengguna hadir. Server web dan cron sinkronisasi Classroom menulis
file yang sama, jadi setiap baca-ubah-tulis memegang GOOGLE_LOCK_FILE.

Isi satu akun: sub, email, name, picture, user_id (pemilik data di agent), scopes,
refresh_token, access_token, access_token_expires_at, status ("ok" / "reauth_required"),
created_at, last_login_at.
"""

from __future__ import annotations

import hashlib
import secrets
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

from edupad.config import (
    GOOGLE_ACCOUNTS_FILE,
    GOOGLE_LOCK_FILE,
    GOOGLE_SESSIONS_FILE,
    Settings,
)
from edupad.core.files import now_iso, read_json, write_json
from edupad.core.lock import wait_for_lock
from edupad.google import oauth

ACCESS_TOKEN_MARGIN = 120  # perbarui access token 2 menit sebelum habis
SESSION_SECONDS = 30 * 24 * 3600
LOCK_TIMEOUT = 30
STATUS_OK = "ok"
STATUS_REAUTH = "reauth_required"


def edupad_user_id(email: str, sub: str, settings: Settings) -> str:
    """Pemilik data di agent: pemilik server (EDUPAD_OWNER_EMAILS) memakai user_id-nya sendiri
    agar Classroom-nya terbaca agent di perangkat/CLI; pengguna lain mendapat ruang sendiri."""
    if email.lower() in settings.owner_emails:
        return settings.user_id
    return f"google-{sub}"


def usable_refresh_token(account: dict | None) -> str | None:
    """Refresh token yang masih bisa dipakai; yang sudah ditolak Google (STATUS_REAUTH) tidak."""
    if not account or account.get("status") == STATUS_REAUTH:
        return None
    return account.get("refresh_token")


def has_classroom(account: dict) -> bool:
    """Izin minimal untuk sinkronisasi: daftar kelas. Izin lain boleh sebagian (granular consent)."""
    return oauth.scope_granted(account.get("scopes"), oauth.CLASSROOM_COURSES)


@contextmanager
def _locked_json(path: Path, lock: Path) -> Iterator[dict]:
    """Isi file JSON untuk diubah; ditulis kembali (0600) saat blok selesai tanpa error."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with wait_for_lock(lock, timeout=LOCK_TIMEOUT, poll=0.1):
        data = read_json(path)
        yield data
        write_json(path, data, private=True)


class AccountStore:
    def __init__(self, path: Path = GOOGLE_ACCOUNTS_FILE, lock: Path = GOOGLE_LOCK_FILE):
        self.path, self.lock = path, lock

    def get(self, sub: str) -> dict | None:
        return read_json(self.path).get(sub)

    def all(self) -> list[dict]:
        return list(read_json(self.path).values())

    def save_login(self, claims: dict, tokens: oauth.Tokens, user_id: str) -> dict:
        sub, now = claims["sub"], now_iso()
        with _locked_json(self.path, self.lock) as accounts:
            old = accounts.get(sub, {})
            account = {
                **old,
                "sub": sub,
                "email": claims["email"],
                "name": claims.get("name") or claims["email"],
                "picture": claims.get("picture"),
                "user_id": user_id,
                # izin yang berlaku untuk token ini (bisa sebagian: granular consent)
                "scopes": sorted(tokens.scopes or old.get("scopes", [])),
                # Google tidak mengirim refresh token lagi untuk izin yang masih berlaku
                "refresh_token": tokens.refresh_token or usable_refresh_token(old),
                "access_token": tokens.access_token,
                "access_token_expires_at": tokens.expires_at,
                "status": STATUS_OK,
                "created_at": old.get("created_at") or now,
                "last_login_at": now,
            }
            accounts[sub] = account
        return dict(account)

    def access_token(
        self, sub: str, client: oauth.Client, now: Callable[[], float] = time.time
    ) -> str:
        """Access token yang masih berlaku, diperbarui lewat refresh token bila perlu.

        ReauthRequired bila refresh token tidak ada atau sudah dicabut/kedaluwarsa; akun
        ditandai agar web meminta login ulang.
        """
        # Error dilempar SETELAH blok `with`: exception di dalamnya membatalkan penulisan,
        # padahal status STATUS_REAUTH harus tersimpan.
        error: oauth.ReauthRequired | None = None
        with _locked_json(self.path, self.lock) as accounts:
            account = accounts.get(sub)
            if account is None:
                raise oauth.GoogleAuthError("akun Google tidak dikenal", "unknown_account")
            expires_at = account.get("access_token_expires_at", 0)
            if account.get("access_token") and expires_at - ACCESS_TOKEN_MARGIN > now():
                return account["access_token"]
            if account.get("status") == STATUS_REAUTH or not account.get("refresh_token"):
                account["status"] = STATUS_REAUTH
                error = oauth.ReauthRequired("refresh token tidak tersedia", "reauth_required")
            else:
                try:
                    tokens = oauth.refresh(client, account["refresh_token"])
                except oauth.ReauthRequired as e:
                    account["status"] = STATUS_REAUTH
                    account.pop("access_token", None)
                    error = e
                else:
                    account["access_token"] = tokens.access_token
                    account["access_token_expires_at"] = tokens.expires_at
                    if tokens.scopes:
                        account["scopes"] = sorted(tokens.scopes)
                    if tokens.refresh_token:
                        account["refresh_token"] = tokens.refresh_token
                    return tokens.access_token
        raise error


def _session_key(token: str) -> str:
    # Yang disimpan hanya hash: file sesi yang bocor tidak bisa dipakai sebagai cookie.
    return hashlib.sha256(token.encode()).hexdigest()


class SessionStore:
    def __init__(
        self,
        path: Path = GOOGLE_SESSIONS_FILE,
        lock: Path = GOOGLE_LOCK_FILE,
        lifetime: int = SESSION_SECONDS,
    ):
        self.path, self.lock, self.lifetime = path, lock, lifetime

    def create(self, sub: str) -> str:
        token = secrets.token_urlsafe(32)
        now = time.time()
        with _locked_json(self.path, self.lock) as sessions:
            for key in [k for k, s in sessions.items() if s.get("expires_at", 0) <= now]:
                del sessions[key]
            sessions[_session_key(token)] = {
                "sub": sub,
                "created_at": now_iso(),
                "expires_at": now + self.lifetime,
            }
        return token

    def get(self, token: str | None) -> str | None:
        """`sub` pemilik sesi, atau None bila tidak ada / kedaluwarsa."""
        if not token:
            return None
        session = read_json(self.path).get(_session_key(token))
        if session and session.get("expires_at", 0) > time.time():
            return session.get("sub")
        return None

    def delete(self, token: str | None) -> None:
        if not token:
            return
        with _locked_json(self.path, self.lock) as sessions:
            sessions.pop(_session_key(token), None)
