"""Koneksi HTTPS yang dipakai ulang ke API luar (DeepSeek, Groq, ElevenLabs, Supabase, Cloudflare).

Koneksi baru butuh 120-250 ms (TCP + TLS) per panggilan, dan satu pertanyaan suara memanggil
API 4-6 kali. Koneksi yang menganggur lebih dari IDLE_SECONDS ditutup dulu agar tidak memakai
koneksi yang sudah diputus diam-diam oleh NAT/firewall; `warm()` membukanya lagi lebih awal.
"""

from __future__ import annotations

import logging
import threading
import time

import requests

log = logging.getLogger(__name__)

IDLE_SECONDS = 60
WARM_TIMEOUT = 5

_sessions: dict[str, requests.Session] = {}
_last_used: dict[str, float] = {}
_lock = threading.Lock()


def session(name: str = "default", headers: dict | None = None) -> requests.Session:
    """Session bersama per nama (`headers` dipakai saat pertama dibuat). Aman antar thread."""
    with _lock:
        http = _sessions.get(name)
        now = time.monotonic()
        if http is None:
            http = _sessions[name] = requests.Session()
            http.headers.update(headers or {})
        elif now - _last_used.get(name, now) > IDLE_SECONDS:
            http.close()  # hanya koneksi menganggur yang ditutup; Session tetap bisa dipakai
        _last_used[name] = now
        return http


def get(url: str, **kwargs) -> requests.Response:
    return session().get(url, **kwargs)


def post(url: str, **kwargs) -> requests.Response:
    return session().post(url, **kwargs)


def warm(*urls: str) -> None:
    """Buka koneksi ke host-host ini di latar belakang (HEAD tanpa API key: tidak ditagih)."""

    def open_connection(url: str) -> None:
        try:
            session().head(url, timeout=WARM_TIMEOUT)
        except requests.RequestException as e:
            log.debug("warm %s gagal: %s", url, e)

    for url in urls:
        threading.Thread(target=open_connection, args=(url,), daemon=True).start()
