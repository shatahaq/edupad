"""Akses Office API memakai sesi login Google dari web EduPad (`edupad serve`).

Office API hanya membaca cookie sesi dan file akun yang ditulis web EduPad; login, logout,
dan izin Classroom tetap ditangani `src/edupad/webapp.py`. Yang boleh masuk hanya pemilik
server (EDUPAD_OWNER_EMAILS), karena dashboard menampilkan data agent milik pemilik.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlsplit

from fastapi import HTTPException, Request

from edupad.config import get_settings
from edupad.google.accounts import AccountStore, SessionStore

SESSION_COOKIE = "edupad_session"  # sama dengan webapp.SESSION_COOKIE
UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


@dataclass(frozen=True)
class Viewer:
    user_id: str
    email: str | None
    name: str | None


def auth_disabled() -> bool:
    """Hanya untuk pengembangan lokal tanpa login Google: EDUPAD_OFFICE_AUTH=off."""
    return os.environ.get("EDUPAD_OFFICE_AUTH", "").strip().lower() == "off"


def _origin(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}".lower()


def allowed_origins() -> set[str]:
    settings = get_settings()
    extra = os.environ.get("EDUPAD_OFFICE_ORIGINS", "")
    return {_origin(settings.public_url)} | {
        _origin(value.strip()) for value in extra.split(",") if value.strip()
    }


def require_owner(request: Request) -> Viewer:
    """Dependency FastAPI: 401 bila belum login, 403 bila bukan pemilik atau beda origin."""
    settings = get_settings()
    if request.method in UNSAFE_METHODS:
        origin = request.headers.get("origin")
        if origin and _origin(origin) not in allowed_origins():
            raise HTTPException(status_code=403, detail="asal permintaan tidak diizinkan")
    if auth_disabled():
        return Viewer(user_id=settings.user_id, email=None, name=None)
    sub = SessionStore().get(request.cookies.get(SESSION_COOKIE))
    account = AccountStore().get(sub) if sub else None
    if not account:
        raise HTTPException(status_code=401, detail="belum login")
    email = str(account.get("email") or "").lower()
    if email not in settings.owner_emails:
        raise HTTPException(
            status_code=403,
            detail="dashboard hanya untuk pemilik EduPad (EDUPAD_OWNER_EMAILS)",
        )
    return Viewer(user_id=settings.user_id, email=email, name=account.get("name"))
