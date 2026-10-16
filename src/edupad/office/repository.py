"""Penyimpanan Office dengan Supabase sebagai target dan file lokal sebagai fallback aman."""

from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from pathlib import Path
from typing import Any

from edupad.config import DATA_DIR, get_settings
from edupad.core.lock import wait_for_lock
from edupad.core.supabase import SupabaseClient, SupabaseError
from edupad.office.models import OfficeEvent, now_iso

log = logging.getLogger(__name__)

OFFICE_DIR = DATA_DIR / "office"
LOCAL_STATE = OFFICE_DIR / "state.json"
TASKS_TABLE = "office_tasks"
EVENTS_TABLE = "office_agent_events"
EXECUTABLE_JOBS = frozenset({"index"})


class OfficeClaimUnavailable(RuntimeError):
    """Storage aktif belum mendukung claim atomik lintas worker."""


def _task_view(row: dict[str, Any]) -> dict[str, Any]:
    """Tambahkan field baru tanpa merusak task lama yang belum memilikinya."""
    return {
        "job_type": "manual",
        "claimed_by": None,
        "claimed_at": None,
        "started_at": None,
        "finished_at": None,
        "error": None,
        "result": None,
        **row,
    }


class FileOfficeRepository:
    """Fallback development. Tidak digunakan bila Supabase Office tersedia."""

    mode = "local"

    def __init__(self, path: Path = LOCAL_STATE):
        self.path = path
        self.lock_path = path.with_suffix(".lock")
        self._lock = threading.Lock()

    def _read(self) -> dict[str, list[dict]]:
        if not self.path.exists():
            return {"tasks": [], "events": []}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"tasks": [], "events": []}

    def _write(self, data: dict[str, list[dict]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.path)

    def list_tasks(self) -> list[dict]:
        with self._lock, wait_for_lock(self.lock_path, timeout=5, poll=0.05):
            return [_task_view(row) for row in self._read()["tasks"]]

    def create_task(self, values: dict[str, Any]) -> dict:
        with self._lock, wait_for_lock(self.lock_path, timeout=5, poll=0.05):
            data = self._read()
            now = now_iso()
            row = {
                "id": str(uuid.uuid4()),
                "status": "queued",
                "priority": "medium",
                "assigned_agent": "coordinator",
                "job_type": "manual",
                "description": "",
                "claimed_by": None,
                "claimed_at": None,
                "started_at": None,
                "finished_at": None,
                "error": None,
                "result": None,
                "created_at": now,
                "updated_at": now,
                **values,
            }
            data["tasks"].insert(0, row)
            self._write(data)
            return row

    def update_task(self, task_id: str, values: dict[str, Any]) -> dict | None:
        with self._lock, wait_for_lock(self.lock_path, timeout=5, poll=0.05):
            data = self._read()
            for row in data["tasks"]:
                if row["id"] == task_id:
                    row.update(values, updated_at=now_iso())
                    self._write(data)
                    return _task_view(row)
            return None

    def claim_next_task(self, worker_id: str, allowed_jobs: frozenset[str]) -> dict | None:
        """Claim task tertua dalam satu critical section lintas thread/proses."""
        with self._lock, wait_for_lock(self.lock_path, timeout=5, poll=0.05):
            data = self._read()
            for row in reversed(data["tasks"]):
                if row.get("status") != "queued" or row.get("job_type") not in allowed_jobs:
                    continue
                now = now_iso()
                row.update(
                    status="in_progress",
                    claimed_by=worker_id,
                    claimed_at=now,
                    started_at=now,
                    updated_at=now,
                    error=None,
                )
                self._write(data)
                return _task_view(row)
        return None

    def finish_claimed_task(
        self,
        task_id: str,
        worker_id: str,
        *,
        status: str,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> dict | None:
        """Selesaikan hanya task yang benar-benar dimiliki worker pemanggil."""
        if status not in {"completed", "failed"}:
            raise ValueError(f"status terminal tidak valid: {status}")
        with self._lock, wait_for_lock(self.lock_path, timeout=5, poll=0.05):
            data = self._read()
            for row in data["tasks"]:
                if row["id"] != task_id:
                    continue
                if row.get("status") != "in_progress" or row.get("claimed_by") != worker_id:
                    return None
                now = now_iso()
                row.update(
                    status=status,
                    result=result,
                    error=error,
                    finished_at=now,
                    updated_at=now,
                )
                self._write(data)
                return _task_view(row)
        return None

    def add_event(self, event: OfficeEvent) -> dict:
        with self._lock, wait_for_lock(self.lock_path, timeout=5, poll=0.05):
            data = self._read()
            last = data["events"][-1]["id"] if data["events"] else 0
            row = {**event.as_dict(), "id": int(last) + 1}
            data["events"].append(row)
            data["events"] = data["events"][-500:]
            self._write(data)
            return row

    def list_events(self, after: int | str | None = None, limit: int = 100) -> list[dict]:
        with self._lock, wait_for_lock(self.lock_path, timeout=5, poll=0.05):
            rows = self._read()["events"]
        if after is not None:
            try:
                marker = int(after)
                rows = [row for row in rows if int(row["id"]) > marker]
            except (TypeError, ValueError):
                pass
        return rows[-limit:]


class SupabaseOfficeRepository:
    mode = "supabase"

    def __init__(self):
        self.settings = get_settings()
        self.db = SupabaseClient()

    @property
    def user_filter(self) -> str:
        return f"eq.{self.settings.user_id}"

    def list_tasks(self) -> list[dict]:
        return [
            _task_view(row)
            for row in self.db.select(
                TASKS_TABLE,
                "id,title,description,status,priority,assigned_agent,due_at,created_at,updated_at",
                user_id=self.user_filter,
                order="created_at.desc",
            )
        ]

    def create_task(self, values: dict[str, Any]) -> dict:
        now = now_iso()
        database_values = {
            key: value
            for key, value in values.items()
            if key in {"title", "description", "status", "priority", "assigned_agent", "due_at"}
        }
        row = {
            "id": str(uuid.uuid4()),
            "user_id": self.settings.user_id,
            "status": "queued",
            "priority": "medium",
            "assigned_agent": "coordinator",
            "description": "",
            "created_at": now,
            "updated_at": now,
            **database_values,
        }
        return _task_view(self.db.insert(TASKS_TABLE, [row])[0])

    def update_task(self, task_id: str, values: dict[str, Any]) -> dict | None:
        self.db.update(
            TASKS_TABLE,
            {**values, "updated_at": now_iso()},
            id=f"eq.{task_id}",
            user_id=self.user_filter,
        )
        rows = self.db.select(
            TASKS_TABLE,
            "id,title,description,status,priority,assigned_agent,due_at,created_at,updated_at",
            id=f"eq.{task_id}",
            user_id=self.user_filter,
            limit="1",
        )
        return rows[0] if rows else None

    def add_event(self, event: OfficeEvent) -> dict:
        row = {"user_id": self.settings.user_id, **event.as_dict()}
        row.pop("id", None)
        return self.db.insert(EVENTS_TABLE, [row])[0]

    def list_events(self, after: int | str | None = None, limit: int = 100) -> list[dict]:
        filters = {
            "user_id": self.user_filter,
            "order": "id.asc",
            "limit": str(limit),
        }
        if after is not None:
            filters["id"] = f"gt.{after}"
        return self.db.select(
            EVENTS_TABLE,
            "id,run_id,agent_id,state,room,job_type,message,progress,metadata,created_at",
            **filters,
        )

    def claim_next_task(self, worker_id: str, allowed_jobs: frozenset[str]) -> dict | None:
        raise OfficeClaimUnavailable(
            "Claim Supabase memerlukan kolom claim dan RPC atomik; migration belum disetujui"
        )


class ResilientOfficeRepository:
    """Gunakan Supabase bila siap; fallback tidak boleh memutus pipeline EduPad."""

    def __init__(self):
        self.local = FileOfficeRepository()
        self.remote: SupabaseOfficeRepository | None = None
        self.mode = "local"
        storage = os.environ.get("EDUPAD_OFFICE_STORAGE", "local").strip().lower()
        if storage == "supabase" and get_settings().supabase_key:
            try:
                self.remote = SupabaseOfficeRepository()
                self.mode = "supabase"
            except SupabaseError as exc:
                log.warning("[office] Supabase tidak tersedia, memakai penyimpanan lokal: %s", exc)

    def _call(self, method: str, *args, **kwargs):
        if self.remote:
            try:
                value = getattr(self.remote, method)(*args, **kwargs)
                self.mode = "supabase"
                return value
            except Exception as exc:  # noqa: BLE001 - fallback menjaga dashboard tetap hidup
                self.mode = "local"
                self.remote = None
                log.warning("[office] %s Supabase gagal, fallback lokal: %s", method, exc)
        return getattr(self.local, method)(*args, **kwargs)

    def list_tasks(self) -> list[dict]:
        return self._call("list_tasks")

    def create_task(self, values: dict[str, Any]) -> dict:
        return self._call("create_task", values)

    def update_task(self, task_id: str, values: dict[str, Any]) -> dict | None:
        return self._call("update_task", task_id, values)

    def add_event(self, event: OfficeEvent) -> dict:
        return self._call("add_event", event)

    def list_events(self, after: int | str | None = None, limit: int = 100) -> list[dict]:
        return self._call("list_events", after, limit)

    @property
    def supports_claiming(self) -> bool:
        return self.remote is None

    def claim_next_task(
        self, worker_id: str, allowed_jobs: frozenset[str] = EXECUTABLE_JOBS
    ) -> dict | None:
        if self.remote is not None:
            return self.remote.claim_next_task(worker_id, allowed_jobs)
        return self.local.claim_next_task(worker_id, allowed_jobs)

    def finish_claimed_task(
        self,
        task_id: str,
        worker_id: str,
        *,
        status: str,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> dict | None:
        if self.remote is not None:
            raise OfficeClaimUnavailable(
                "Penyelesaian claim Supabase belum tersedia sebelum migration disetujui"
            )
        return self.local.finish_claimed_task(
            task_id,
            worker_id,
            status=status,
            result=result,
            error=error,
        )


_repository: ResilientOfficeRepository | None = None
_repository_lock = threading.Lock()


def get_repository() -> ResilientOfficeRepository:
    global _repository
    with _repository_lock:
        if _repository is None:
            _repository = ResilientOfficeRepository()
        return _repository
