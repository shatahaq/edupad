import threading
import time
from concurrent.futures import ThreadPoolExecutor

from tests.fakes import FakeDb

from edupad.office import events
from edupad.office.chat_history import list_recent_iot_chats
from edupad.office.models import OfficeEvent
from edupad.office.repository import FileOfficeRepository
from edupad.office.router import INDEX_ROUTE, JobRouter
from edupad.office.worker import OfficeWorker


def _index_task(repo: FileOfficeRepository):
    return repo.create_task(
        {
            "title": "Indeks materi",
            "description": "",
            "priority": "high",
            "assigned_agent": "researcher",
            "job_type": "index",
        }
    )


class SuccessfulRouter:
    allowed_job_types = frozenset({"index"})

    def route_for(self, task):
        return INDEX_ROUTE

    def run(self, task, on_progress=None):
        if on_progress:
            on_progress(3, 4)
        return {"exit_code": 0}


class FailingRouter(SuccessfulRouter):
    def run(self, task, on_progress=None):
        raise RuntimeError("embedding gagal")


def test_office_repository_stores_tasks_and_events(tmp_path):
    repo = FileOfficeRepository(tmp_path / "office.json")
    task = repo.create_task(
        {
            "title": "Indeks materi",
            "description": "",
            "priority": "high",
            "assigned_agent": "researcher",
        }
    )
    assert repo.list_tasks()[0]["title"] == "Indeks materi"

    updated = repo.update_task(task["id"], {"status": "completed"})
    assert updated and updated["status"] == "completed"

    row = repo.add_event(
        OfficeEvent(
            agent_id="researcher",
            state="running",
            room="research-lab",
            job_type="index",
            message="Membuat embedding",
            progress=45,
        )
    )
    assert repo.list_events(after=0) == [row]


def test_snapshot_uses_latest_real_agent_event(monkeypatch, tmp_path):
    repo = FileOfficeRepository(tmp_path / "office.json")
    repo.add_event(
        OfficeEvent(
            agent_id="keeper",
            state="running",
            room="knowledge-server",
            job_type="corpus",
            message="Menyusun knowledge base",
            progress=64,
        )
    )
    monkeypatch.setattr(events, "get_repository", lambda: repo)

    snapshot = events.build_snapshot()
    keeper = next(agent for agent in snapshot["agents"] if agent["id"] == "keeper")
    assert keeper["state"] == "running"
    assert keeper["progress"] == 64
    assert keeper["task"] == "Menyusun knowledge base"


def test_worker_completes_index_task_and_emits_real_progress(tmp_path):
    repo = FileOfficeRepository(tmp_path / "office.json")
    task = _index_task(repo)
    emitted = []

    def capture(agent_id, state, **values):
        emitted.append((agent_id, state.value, values))

    worker = OfficeWorker(
        repository=repo,
        router=SuccessfulRouter(),
        emitter=capture,
        worker_id="worker-success",
    )
    assert worker.run_once() is True

    stored = next(row for row in repo.list_tasks() if row["id"] == task["id"])
    assert stored["status"] == "completed"
    assert stored["claimed_by"] == "worker-success"
    assert [row[1] for row in emitted] == ["running", "running", "succeeded"]
    assert emitted[1][2]["progress"] == 75
    assert emitted[1][2]["metadata"]["chunks_completed"] == 3
    assert emitted[-1][2]["station_id"] == "knowledge-index-01"


def test_worker_marks_index_task_failed(tmp_path):
    repo = FileOfficeRepository(tmp_path / "office.json")
    task = _index_task(repo)
    emitted = []

    def capture(agent_id, state, **values):
        emitted.append((agent_id, state.value, values))

    worker = OfficeWorker(
        repository=repo,
        router=FailingRouter(),
        emitter=capture,
        worker_id="worker-failure",
    )
    assert worker.run_once() is True

    stored = next(row for row in repo.list_tasks() if row["id"] == task["id"])
    assert stored["status"] == "failed"
    assert "embedding gagal" in stored["error"]
    assert emitted[-1][1] == "failed"
    assert emitted[-1][2]["activity"] == "failed"


def test_two_workers_cannot_execute_same_task(tmp_path):
    path = tmp_path / "office.json"
    _index_task(FileOfficeRepository(path))
    calls = 0
    calls_lock = threading.Lock()

    class SlowRouter(SuccessfulRouter):
        def run(self, task, on_progress=None):
            nonlocal calls
            with calls_lock:
                calls += 1
            time.sleep(0.05)
            return {"exit_code": 0}

    workers = [
        OfficeWorker(
            repository=FileOfficeRepository(path),
            router=SlowRouter(),
            emitter=lambda *args, **kwargs: None,
            worker_id=f"worker-{number}",
        )
        for number in range(2)
    ]
    with ThreadPoolExecutor(max_workers=2) as pool:
        processed = list(pool.map(lambda worker: worker.run_once(), workers))

    assert sorted(processed) == [False, True]
    assert calls == 1
    assert FileOfficeRepository(path).list_tasks()[0]["status"] == "completed"


def test_job_router_calls_existing_index_function(monkeypatch):
    calls = []

    def fake_index(*, force, on_progress):
        calls.append((force, on_progress))
        return 0

    monkeypatch.setattr("edupad.processing.index.run", fake_index)

    def progress(completed, total):
        return None

    result = JobRouter().run({"job_type": "index"}, on_progress=progress)

    assert result == {"exit_code": 0}
    assert calls == [(False, progress)]


def test_iot_chat_history_reuses_existing_agent_turns_table():
    db = FakeDb()
    db.insert(
        "agent_turns",
        [
            {
                "session_id": "session-1",
                "user_id": "student-1",
                "question": "Apa jadwal saya?",
                "speech": "Ada kelas pukul sembilan.",
                "screen": ["Kelas 09.00"],
                "detail": "tidak boleh ikut terkirim",
                "created_at": "2026-10-13T09:00:00+07:00",
            }
        ],
    )

    rows = list_recent_iot_chats(db=db, user_id="student-1")

    assert rows == [
        {
            "id": 1,
            "session_id": "session-1",
            "question": "Apa jadwal saya?",
            "answer": "Ada kelas pukul sembilan.",
            "screen": ["Kelas 09.00"],
            "created_at": "2026-10-13T09:00:00+07:00",
        }
    ]
    assert "detail" not in rows[0]
