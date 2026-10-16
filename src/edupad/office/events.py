"""Event status best-effort agar observability tidak pernah merusak pekerjaan utama."""

from __future__ import annotations

import atexit
import logging
import queue
import threading
from typing import Any

from edupad.office.models import AGENTS, AgentState, OfficeEvent, default_agent_rows
from edupad.office.repository import get_repository

log = logging.getLogger(__name__)

# Status dikirim dari antrean latar belakang: jawaban perangkat (/v1/ask) dan pipeline tidak
# menunggu penulisan file/Supabase. Satu thread menjaga urutan event per proses.
_QUEUE: queue.Queue[OfficeEvent | None] = queue.Queue(maxsize=1000)
_writer: threading.Thread | None = None
_writer_lock = threading.Lock()
FLUSH_TIMEOUT = 3.0


def _store(event: OfficeEvent) -> dict | None:
    try:
        return get_repository().add_event(event)
    except Exception as exc:  # noqa: BLE001 - telemetry tidak boleh menggagalkan pekerjaan utama
        log.warning("[office] status tidak tersimpan: %s", exc)
        return None


def _drain() -> None:
    while True:
        event = _QUEUE.get()
        try:
            if event is not None:
                _store(event)
        finally:
            _QUEUE.task_done()


def _enqueue(event: OfficeEvent) -> None:
    global _writer
    with _writer_lock:
        if _writer is None or not _writer.is_alive():
            _writer = threading.Thread(target=_drain, name="office-events", daemon=True)
            _writer.start()
    try:
        _QUEUE.put_nowait(event)
    except queue.Full:
        log.warning("[office] antrean status penuh; event %s dilewati", event.job_type)


def flush(timeout: float = FLUSH_TIMEOUT) -> None:
    """Tunggu antrean kosong (dipanggil saat proses selesai agar event terakhir tersimpan)."""
    if _writer is None:
        return
    done = threading.Event()
    threading.Thread(target=lambda: (_QUEUE.join(), done.set()), daemon=True).start()
    done.wait(timeout)


atexit.register(flush)


def emit_status(
    agent_id: str,
    state: AgentState | str,
    *,
    room: str | None = None,
    job_type: str = "system",
    message: str = "",
    progress: int = 0,
    run_id: str | None = None,
    activity: str | None = None,
    station_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    wait: bool = False,
) -> dict | None:
    """Publikasikan status. Semua kegagalan ditelan agar fungsi EduPad lama tetap aman.

    Default tidak menunggu penyimpanan (kembali None); `wait=True` menyimpan langsung dan
    mengembalikan baris event."""
    definition = next((agent for agent in AGENTS if agent.id == agent_id), AGENTS[0])
    try:
        event_metadata = dict(metadata or {})
        if activity is not None:
            event_metadata["activity"] = activity
        if station_id is not None:
            event_metadata["station_id"] = station_id
        event = OfficeEvent(
            agent_id=agent_id,
            state=state.value if isinstance(state, AgentState) else state,
            room=room or definition.room,
            job_type=job_type,
            message=message,
            progress=max(0, min(int(progress), 100)),
            run_id=run_id,
            metadata=event_metadata,
        )
    except Exception as exc:  # noqa: BLE001 - telemetry tidak boleh menggagalkan pekerjaan utama
        log.warning("[office] status tidak valid: %s", exc)
        return None
    if wait:
        return _store(event)
    _enqueue(event)
    return None


def build_snapshot() -> dict[str, Any]:
    repo = get_repository()
    events = repo.list_events(limit=100)
    agents = {row["id"]: row for row in default_agent_rows()}
    for event in events:
        agent = agents.get(event["agent_id"])
        if not agent:
            continue
        metadata = event.get("metadata") or {}
        agent.update(
            state=event["state"],
            room=event["room"],
            task=event["message"] or event["job_type"],
            progress=event.get("progress", 0),
            updated_at=event["created_at"],
            activity=metadata.get("activity", "idle"),
            station_id=metadata.get("station_id"),
        )
    tasks = repo.list_tasks()
    active_states = {"queued", "running", "waiting"}
    return {
        "status": "ok",
        "source": repo.mode,
        "agents": list(agents.values()),
        "tasks": tasks,
        "recent_events": list(reversed(events[-20:])),
        "last_event_id": events[-1]["id"] if events else None,
        "metrics": {
            "active_agents": sum(a["state"] in active_states for a in agents.values()),
            "queued_tasks": sum(t.get("status") == "queued" for t in tasks),
            "completed_tasks": sum(t.get("status") == "completed" for t in tasks),
            "knowledge_health": 100,
        },
    }
