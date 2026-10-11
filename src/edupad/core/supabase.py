"""Klien REST Supabase (PostgREST) minimal.

Dipakai dari server dengan secret key (role service_role), karena tabel
dilindungi RLS tanpa policy: key publik (anon) tidak bisa membaca apa pun.
"""

from __future__ import annotations

import requests

from edupad.config import REQUEST_TIMEOUT, get_settings
from edupad.core import http_pool

PAGE_SIZE = 1000


class SupabaseError(RuntimeError):
    pass


class SupabaseClient:
    def __init__(self, url: str | None = None, key: str | None = None):
        settings = get_settings()
        self.url = (url or settings.supabase_url).rstrip("/") + "/rest/v1"
        key = key or settings.supabase_key
        if not key:
            raise SupabaseError("SUPABASE_SECRET_KEY belum diisi di .env")
        # Session bersama: memory & pencarian materi tidak membuka koneksi TLS baru tiap pertanyaan.
        self.http = http_pool.session(
            f"supabase {self.url} {key}",
            {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )

    def _check(self, response: requests.Response) -> requests.Response:
        if not response.ok:
            raise SupabaseError(f"HTTP {response.status_code}: {response.text[:300]}")
        return response

    def select(self, table: str, columns: str, **filters: str) -> list[dict]:
        """filters memakai sintaks PostgREST, mis. user_id='eq.default', order='id.desc'."""
        rows, start = [], 0
        while True:
            response = self._check(
                self.http.get(
                    f"{self.url}/{table}",
                    params={"select": columns, **filters},
                    headers={"Range": f"{start}-{start + PAGE_SIZE - 1}"},
                    timeout=REQUEST_TIMEOUT,
                )
            )
            page = response.json()
            rows += page
            if len(page) < PAGE_SIZE:
                return rows
            start += PAGE_SIZE

    def upsert(self, table: str, rows: list[dict], on_conflict: str) -> None:
        self._check(
            self.http.post(
                f"{self.url}/{table}",
                params={"on_conflict": on_conflict},
                json=rows,
                headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
                timeout=120,
            )
        )

    def insert(self, table: str, rows: list[dict]) -> list[dict]:
        return self._check(
            self.http.post(
                f"{self.url}/{table}",
                json=rows,
                headers={"Prefer": "return=representation"},
                timeout=REQUEST_TIMEOUT,
            )
        ).json()

    def update(self, table: str, values: dict, **filters: str) -> None:
        self._check(
            self.http.patch(
                f"{self.url}/{table}",
                params=filters,
                json=values,
                headers={"Prefer": "return=minimal"},
                timeout=REQUEST_TIMEOUT,
            )
        )

    def delete(self, table: str, **filters: str) -> None:
        self._check(
            self.http.delete(f"{self.url}/{table}", params=filters, timeout=REQUEST_TIMEOUT)
        )

    def rpc(self, function: str, **args: object) -> list[dict]:
        return self._check(
            self.http.post(f"{self.url}/rpc/{function}", json=args, timeout=REQUEST_TIMEOUT)
        ).json()
