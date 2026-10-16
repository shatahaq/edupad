"""Model data stabil antara backend EduPad dan frontend Office."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from edupad.config import WIB


class AgentState(str, Enum):
    OFFLINE = "offline"
    IDLE = "idle"
    QUEUED = "queued"
    RUNNING = "running"
    WAITING = "waiting"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class AgentDefinition:
    id: str
    name: str
    role: str
    room: str
    color: str


AGENTS = (
    AgentDefinition("coordinator", "NOVA", "Koordinator asisten AI", "command-center", "#22d3ee"),
    AgentDefinition("researcher", "PIXEL", "Pengolah materi kuliah", "research-lab", "#60a5fa"),
    AgentDefinition("tutor", "SORA", "Tutor belajar", "tutor-room", "#facc15"),
    AgentDefinition("planner", "TEMPO", "Pengatur jadwal belajar", "planning-hub", "#a78bfa"),
    AgentDefinition("analyst", "METRIC", "Pemantau progres belajar", "analytics-room", "#34d399"),
    AgentDefinition("finance", "KOIN", "Pengelola keuangan mahasiswa", "finance-office", "#34a86f"),
    AgentDefinition("keeper", "NEXUS", "Penjaga data pengetahuan", "knowledge-server", "#fb7185"),
)


# Owl & ruangan yang bekerja saat AI agent memanggil tool (dipakai ask() untuk event Office).
TOOL_AGENTS: dict[str, tuple[str, str]] = {
    "search_materials": ("keeper", "knowledge-server"),
    "get_meeting": ("researcher", "research-lab"),
    "get_classroom_materials": ("researcher", "research-lab"),
    "list_assignments": ("planner", "planning-hub"),
    "get_attendance": ("planner", "planning-hub"),
    "study_plan": ("planner", "planning-hub"),
    "remember": ("tutor", "tutor-room"),
    "start_quiz": ("tutor", "tutor-room"),
    "answer_quiz": ("tutor", "tutor-room"),
    "stop_quiz": ("tutor", "tutor-room"),
    "start_help": ("tutor", "tutor-room"),
    "continue_help": ("tutor", "tutor-room"),
    "decline_help": ("tutor", "tutor-room"),
    "record_transaction": ("finance", "finance-office"),
    "finance_summary": ("finance", "finance-office"),
    "undo_last_transaction": ("finance", "finance-office"),
    "set_budget": ("finance", "finance-office"),
}


def now_iso() -> str:
    return datetime.now(WIB).isoformat()


@dataclass
class OfficeEvent:
    agent_id: str
    state: str
    room: str
    job_type: str
    message: str
    progress: int = 0
    run_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=now_iso)
    id: int | str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_agent_rows() -> list[dict[str, Any]]:
    updated = now_iso()
    return [
        {
            **asdict(agent),
            "state": AgentState.IDLE.value,
            "task": "Menunggu tugas",
            "progress": 0,
            "activity": "idle",
            "station_id": None,
            "updated_at": updated,
        }
        for agent in AGENTS
    ]
