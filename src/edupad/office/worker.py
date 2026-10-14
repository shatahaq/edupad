"""Worker tunggal untuk mengeksekusi task Office yang sudah di-claim."""

from __future__ import annotations

import logging
import socket
import time
import uuid
from collections.abc import Callable

from edupad.errors import EXIT_ERROR, EXIT_OK
from edupad.office.events import emit_status
from edupad.office.models import AgentState
from edupad.office.repository import OfficeClaimUnavailable, get_repository
from edupad.office.router import JobRouter

log = logging.getLogger(__name__)

EventEmitter = Callable[..., dict | None]


class OfficeWorker:
    def __init__(
        self,
        repository=None,
        router: JobRouter | None = None,
        emitter: EventEmitter = emit_status,
        worker_id: str | None = None,
    ):
        self.repository = repository or get_repository()
        self.router = router or JobRouter()
        self.emitter = emitter
        self.worker_id = worker_id or f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"

    def run_once(self) -> bool:
        task = self.repository.claim_next_task(
            self.worker_id, frozenset(self.router.allowed_job_types)
        )
        if task is None:
            return False

        route = self.router.route_for(task)
        task_id = task["id"]
        run_id = f"office-{task_id}"
        common = {
            "room": route.room,
            "job_type": task["job_type"],
            "run_id": run_id,
            "activity": route.activity,
            "station_id": route.station_id,
        }
        self.emitter(
            route.agent_id,
            AgentState.RUNNING,
            message="Menuju ruang server untuk mengolah materi",
            progress=0,
            metadata={"task_id": task_id},
            **common,
        )

        def report_progress(completed: int, total: int) -> None:
            progress = round(completed * 100 / total) if total else 0
            self.emitter(
                route.agent_id,
                AgentState.RUNNING,
                message=f"Memproses bagian materi {completed}/{total}",
                progress=progress,
                metadata={
                    "task_id": task_id,
                    "chunks_completed": completed,
                    "chunks_total": total,
                },
                **common,
            )

        try:
            result = self.router.run(task, on_progress=report_progress)
        except Exception as exc:  # noqa: BLE001 - worker wajib menandai task terminal
            error = f"{type(exc).__name__}: {exc}"[:1000]
            log.exception("[office-worker] task %s gagal", task_id)
            self.repository.finish_claimed_task(
                task_id,
                self.worker_id,
                status="failed",
                error=error,
            )
            self.emitter(
                route.agent_id,
                AgentState.FAILED,
                message="Materi belum berhasil diproses",
                progress=100,
                activity="failed",
                metadata={"task_id": task_id, "error": error},
                **{key: value for key, value in common.items() if key != "activity"},
            )
            return True

        finished = self.repository.finish_claimed_task(
            task_id,
            self.worker_id,
            status="completed",
            result=result,
        )
        if finished is None:
            log.error("[office-worker] claim task %s berubah sebelum diselesaikan", task_id)
            return True
        self.emitter(
            route.agent_id,
            AgentState.SUCCEEDED,
            message="Materi berhasil diperbarui",
            progress=100,
            activity="completed",
            metadata={"task_id": task_id, **result},
            **{key: value for key, value in common.items() if key != "activity"},
        )
        return True


def run(once: bool = False, poll_interval: float = 1.0) -> int:
    worker = OfficeWorker()
    delay = max(0.2, poll_interval)
    log.info("[office-worker] aktif sebagai %s", worker.worker_id)
    try:
        if once:
            worker.run_once()
            return EXIT_OK
        while True:
            if not worker.run_once():
                time.sleep(delay)
    except OfficeClaimUnavailable as exc:
        log.error("[office-worker] %s", exc)
        return EXIT_ERROR
    except KeyboardInterrupt:
        log.info("[office-worker] berhenti")
        return EXIT_OK
