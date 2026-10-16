"""Whitelist job Office yang boleh memanggil fungsi EduPad asli."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from edupad.errors import EXIT_OK


class UnsupportedOfficeJob(ValueError):
    pass


class OfficeJobFailed(RuntimeError):
    pass


@dataclass(frozen=True)
class JobRoute:
    agent_id: str
    room: str
    station_id: str
    activity: str


INDEX_ROUTE = JobRoute(
    agent_id="researcher",
    room="knowledge-server",
    station_id="knowledge-index-01",
    activity="indexing",
)


class JobRouter:
    """Dispatcher eksplisit; input pengguna tidak pernah menjadi perintah shell."""

    allowed_job_types = frozenset({"index"})

    def route_for(self, task: dict[str, Any]) -> JobRoute:
        if task.get("job_type") != "index":
            raise UnsupportedOfficeJob(f"job tidak diizinkan: {task.get('job_type')!r}")
        return INDEX_ROUTE

    def run(
        self,
        task: dict[str, Any],
        on_progress: Callable[[int, int], None] | None = None,
    ) -> dict[str, Any]:
        self.route_for(task)
        from edupad.processing import index

        exit_code = index.run(force=False, on_progress=on_progress)
        if exit_code != EXIT_OK:
            raise OfficeJobFailed(f"indexing selesai dengan kode {exit_code}")
        return {"exit_code": exit_code}
