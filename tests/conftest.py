import pytest

from edupad import device_status
from edupad.agent import coach, radar, tutor
from edupad.office import events, repository
from edupad.voice import clips
from edupad.voice import mode as voice_mode


@pytest.fixture(autouse=True)
def _office_state_in_tmp(tmp_path, monkeypatch):
    """Status Office dari ask()/pipeline saat tes ditulis ke folder sementara, bukan data/."""
    repo = repository.ResilientOfficeRepository.__new__(repository.ResilientOfficeRepository)
    repo.local = repository.FileOfficeRepository(tmp_path / "office" / "state.json")
    repo.remote = None
    repo.mode = "local"
    monkeypatch.setattr(repository, "_repository", repo)
    monkeypatch.setattr(device_status, "STATUS_FILE", tmp_path / "device" / "status.json")
    monkeypatch.setattr(device_status, "_state", {})
    monkeypatch.setattr(tutor, "BANK_FILE", tmp_path / "tutor" / "bank.json")
    monkeypatch.setattr(voice_mode, "SETTINGS_FILE", tmp_path / "device" / "voice_mode.json")
    monkeypatch.setattr(voice_mode, "EVENTS_FILE", tmp_path / "device" / "voice_events.jsonl")
    monkeypatch.setattr(clips, "CLIPS_DIR", tmp_path / "voice" / "clips")
    yield
    events.flush()


@pytest.fixture(autouse=True)
def _no_supabase_for_tutor_radar(monkeypatch):
    """Kuis aktif & kartu radar tidak membaca Supabase asli saat tes (tes khusus menimpanya)."""
    monkeypatch.setattr(tutor, "prefetch", lambda user_id=None: None)
    monkeypatch.setattr(tutor, "_load_quiz", lambda user_id=None: None)
    monkeypatch.setattr(coach, "prefetch", lambda user_id=None: None)
    monkeypatch.setattr(radar, "device_alerts", lambda now=None, cached=True: [])
    yield
    events.flush()
