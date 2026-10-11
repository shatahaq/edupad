"""Optimasi latensi: koneksi dipakai ulang, memory disiapkan lebih awal, giliran disimpan belakangan."""

import json
import threading
import time

import pytest

from edupad import server as srv
from edupad.agent import assistant
from edupad.agent.memory import ConversationMemory
from edupad.core import http_pool
from fakes import FakeDb


class FakeSession:
    def __init__(self):
        self.closed, self.heads = 0, []

    def close(self):
        self.closed += 1

    def head(self, url, **kwargs):
        self.heads.append((url, kwargs))


@pytest.fixture
def pool(monkeypatch):
    fake = FakeSession()
    monkeypatch.setattr(http_pool, "_sessions", {"default": fake})
    monkeypatch.setattr(http_pool, "_last_used", {"default": time.monotonic()})
    return fake


def test_session_is_shared_and_idle_connections_are_dropped(pool, monkeypatch):
    assert http_pool.session() is http_pool.session() is pool and pool.closed == 0
    later = time.monotonic() + http_pool.IDLE_SECONDS + 1
    monkeypatch.setattr(http_pool.time, "monotonic", lambda: later)
    assert http_pool.session() is pool and pool.closed == 1  # tetap Session yang sama
    named = http_pool.session("supabase x", {"apikey": "k"})
    assert named is http_pool.session("supabase x") and named.headers["apikey"] == "k"


def test_warm_sends_head_without_api_keys(pool):
    http_pool.warm("https://api.groq.com", "https://api.deepseek.com")
    deadline = time.time() + 2
    while len(pool.heads) < 2 and time.time() < deadline:
        time.sleep(0.01)
    assert sorted(url for url, _ in pool.heads) == [
        "https://api.deepseek.com",
        "https://api.groq.com",
    ]
    assert all("headers" not in kw for _, kw in pool.heads)


def test_server_warms_only_api_hosts():
    assert srv.WARM_URLS == (
        "https://api.groq.com",
        "https://api.deepseek.com",
        "https://api.elevenlabs.io",
    )


def test_prefetched_history_is_used_once():
    db = FakeDb()
    ConversationMemory("u1", new_session=True, db=db).save_turn(
        "apa itu xor?",
        {"speech": "x", "screen": {"lines": []}, "detail": "", "sources": [], "usage": {}},
    )
    mem = ConversationMemory("u1", db=db)
    mem.prefetch()
    db.tables["agent_turns"].clear()  # bukti: history() pertama tidak membaca database lagi
    assert mem.history()[0]["content"] == "apa itu xor?"
    assert mem.history() == []


class FakeMemory:
    def __init__(self, events):
        self.events = events

    def history(self):
        return []

    def facts(self):
        return []

    def save_turn(self, question, result):
        self.events.append(("save", question))

    def maybe_summarize(self, complete):
        return False


@pytest.fixture
def fake_llm(monkeypatch, tmp_path):
    calls = []
    answer = {"speech": "halo", "screen_title": "T", "screen_lines": ["a"]}

    def chat(messages, tools=None, json_mode=False):
        calls.append(messages)
        return {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "id": "1",
                                "function": {
                                    "name": assistant.ANSWER_TOOL,
                                    "arguments": json.dumps(answer),
                                },
                            }
                        ]
                    }
                }
            ],
            "usage": {},
        }

    monkeypatch.setattr(assistant, "_chat", chat)
    monkeypatch.setattr(assistant, "USAGE_LOG", tmp_path / "usage.jsonl")
    return calls


def test_ask_saves_now_by_default_and_later_with_defer_save(fake_llm):
    events = []
    assistant.ask("satu", memory=FakeMemory(events))
    assert events == [("save", "satu")]  # CLI: tetap disimpan sebelum ask() kembali

    jobs = []
    result = assistant.ask("dua", memory=FakeMemory(events), defer_save=jobs.append)
    assert result["speech"] == "halo" and events == [("save", "satu")]
    jobs[0]()
    assert events == [("save", "satu"), ("save", "dua")]
    assert len(fake_llm) == 2  # satu panggilan LLM per pertanyaan, tidak ada tambahan


def test_agent_loads_next_memory_only_after_previous_turn_is_saved(monkeypatch):
    events = []
    monkeypatch.setattr(srv.http_pool, "warm", lambda *urls: events.append("warm"))

    class SlowMemory(FakeMemory):
        def prefetch(self):
            events.append("load")

    monkeypatch.setattr(assistant, "open_memory", lambda new_session=False: SlowMemory(events))

    def fake_ask(question, memory, defer_save):
        def save():
            time.sleep(0.2)  # Supabase lambat
            memory.save_turn(question, {})

        defer_save(save)
        return {"speech": question, "screen": {}}

    monkeypatch.setattr(assistant, "ask", fake_ask)
    agent = srv.Agent()
    started = time.time()
    agent.answer("satu", agent.prepare(False))
    assert time.time() - started < 0.15  # jawaban tidak menunggu penyimpanan
    agent.answer("dua", agent.prepare(False))
    agent.close()  # menunggu penyimpanan yang tertunda
    assert events == ["warm", "load", "warm", ("save", "satu"), "load", ("save", "dua")]


def test_agent_answers_without_memory_when_supabase_fails(monkeypatch):
    def broken(new_session=False):
        raise ConnectionError("supabase tidak bisa dihubungi")

    monkeypatch.setattr(srv.http_pool, "warm", lambda *urls: None)
    monkeypatch.setattr(assistant, "open_memory", broken)
    seen = []
    monkeypatch.setattr(assistant, "ask", lambda q, memory, defer_save: seen.append(memory) or {})
    agent = srv.Agent()
    agent.answer("halo", agent.prepare(False))
    agent.close()
    assert seen == [None]


def test_background_save_errors_are_logged_not_lost(caplog):
    def broken():
        raise RuntimeError("HTTP 500")

    agent = srv.Agent()
    agent._save_later(broken)
    agent.close()
    assert "giliran gagal disimpan" in caplog.text and "HTTP 500" in caplog.text


def test_concurrent_sessions_are_thread_safe(monkeypatch):
    monkeypatch.setattr(http_pool, "_sessions", {})
    monkeypatch.setattr(http_pool, "_last_used", {})
    got = []
    threads = [
        threading.Thread(target=lambda: got.append(http_pool.session("x"))) for _ in range(20)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len({id(s) for s in got}) == 1
