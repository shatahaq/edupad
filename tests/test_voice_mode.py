"""Mode Suara: EduPad dipakai tanpa melihat layar (voice/mode.py, voice/clips.py)."""

import json
from array import array

import pytest
from tests.test_latency import FakeMemory, fake_llm  # noqa: F401 - fixture
from tests.test_server import fake_tts, request, server  # noqa: F401 - fixture

from edupad.agent import assistant, tools
from edupad.agent.formatting import MAX_SPEECH_CHARS, VOICE_MODE_SPEECH_CHARS
from edupad.office import dashboard_data
from edupad.voice import clips
from edupad.voice import mode as voice_mode


# ------------------------------- pengaturan --------------------------------
def test_settings_default_save_and_reject_unknown_speed():
    assert voice_mode.load() == {"enabled": False, "speed": "normal"}
    assert voice_mode.save(enabled=True) == {"enabled": True, "speed": "normal"}
    assert voice_mode.save(speed="cepat") == {"enabled": True, "speed": "cepat"}
    assert voice_mode.enabled() and voice_mode.speed_value() == voice_mode.SPEEDS["cepat"]
    with pytest.raises(ValueError):
        voice_mode.save(speed="kilat")
    assert voice_mode.load()["speed"] == "cepat"


def test_voice_tool_toggles_mode_and_reports_errors():
    result = tools.TOOLS["set_voice_mode"](enabled=True, speed="sangat_cepat")
    assert result["mode_suara"] == "aktif" and result["kecepatan"] == "sangat cepat"
    assert tools.TOOLS["set_voice_mode"](enabled=False)["mode_suara"] == "mati"
    assert "error" in tools.TOOLS["set_voice_mode"]()
    assert "error" in tools.TOOLS["set_voice_mode"](speed="kilat")


def test_usage_counts_recent_spoken_answers_and_alerts():
    for event in ("answer", "answer", "alert", "lainnya"):
        voice_mode.record(event)
    assert voice_mode.usage(30) == {"answer": 2, "alert": 1}


# ---------------------------------- agent -----------------------------------
def test_prompt_and_answer_schema_follow_voice_mode(monkeypatch):
    monkeypatch.setattr(assistant, "course_overview", lambda: "-")
    normal, voice = assistant._system_prompt(voice=False), assistant._system_prompt(voice=True)
    assert "set_voice_mode" in normal and "MODE SUARA AKTIF" not in normal
    assert "MODE SUARA AKTIF" in voice and voice.startswith(normal.split("Memory:")[0][:200])
    speech = tools.answer_schema(False, voice=True)["function"]["parameters"]["properties"]
    assert speech["speech"]["description"] == tools.VOICE_SPEECH_DESCRIPTION
    assert (
        tools.answer_schema(False)["function"]["parameters"]["properties"]["speech"]["description"]
        != tools.VOICE_SPEECH_DESCRIPTION
    )


def test_voice_mode_keeps_longer_speech():
    long = json.dumps({"speech": "Kalimat lengkap yang dibacakan. " * 40})
    assert len(assistant._final(long)["speech"]) <= MAX_SPEECH_CHARS
    spoken = assistant._final(long, voice=True)["speech"]
    assert MAX_SPEECH_CHARS < len(spoken) <= VOICE_MODE_SPEECH_CHARS


def test_ask_sends_voice_rules_only_when_enabled(fake_llm, monkeypatch):  # noqa: F811
    monkeypatch.setattr(assistant, "course_overview", lambda: "-")
    assistant.ask("halo", memory=FakeMemory([]))
    voice_mode.save(enabled=True)
    assistant.ask("halo lagi", memory=FakeMemory([]))
    first, second = (messages[0]["content"] for messages in fake_llm)
    assert "MODE SUARA AKTIF" not in first and "MODE SUARA AKTIF" in second


# --------------------------------- perangkat --------------------------------
ALERT = {
    "id": "due:abc:2026-10-17",
    "kind": "deadline",
    "course": "Prak MSBD",
    "detail": "ERD",
    "when": "Besok 23:59",
    "from_ts": 0,
    "to_ts": 1,
    "speech": "Pengingat tugas praktikum MSBD: **ERD**. Batasnya besok pukul 23.59.",
}


@pytest.fixture
def device_updates(monkeypatch):
    from edupad import server as srv

    monkeypatch.setattr(
        srv.updates,
        "updates",
        lambda extra_cards=False: {"now_ts": 1, "next_class": None, "alerts": [dict(ALERT)]},
    )


def _updates(server):  # noqa: F811
    response, data = request(server, "GET", "/v1/updates", headers={"X-Firmware": "1.2"})
    assert response.status == 200
    return json.loads(data)


def test_updates_have_no_voice_extras_when_mode_is_off(server, device_updates):  # noqa: F811
    body = _updates(server)
    assert body["voice_mode"] is False and "voice_clips" not in body
    assert "audio_url" not in body["alerts"][0]


def test_alert_is_spoken_once_and_cached(server, device_updates, fake_tts):  # noqa: F811
    voice_mode.save(enabled=True, speed="cepat")
    body = _updates(server)
    assert body["voice_mode"] is True
    assert body["voice_clips"]["wifi"].startswith("/v1/voice/clip/wifi?v=")
    url = body["alerts"][0]["audio_url"]
    assert url == _updates(server)["alerts"][0]["audio_url"]  # pemberitahuan sama, kunci sama

    for _ in range(2):
        response, pcm = request(server, "GET", url)
        assert response.status == 200 and pcm == b"\x01\x02\x03\x04\x05"
    assert fake_tts == ["Pengingat tugas praktikum MSBD: ERD. Batasnya besok pukul 23.59."]
    assert voice_mode.usage()["alert"] == 2
    assert request(server, "GET", "/v1/speech/tidakada")[0].status == 404


def test_answer_reports_voice_mode_and_uses_chosen_speed(server, monkeypatch):  # noqa: F811
    from edupad import server as srv

    speeds = []

    def stream(text, speed=None):
        speeds.append(speed)
        yield b"\x01\x02"

    monkeypatch.setattr(srv.tts, "stream", stream)
    voice_mode.save(enabled=True, speed="lambat")
    response, data = request(
        server,
        "POST",
        "/v1/ask",
        json.dumps({"text": "halo"}),
        {"Content-Type": "application/json"},
    )
    body = json.loads(data)
    assert body["voice_mode"] is True and set(body["voice_clips"]) == set(clips.CLIPS)
    request(server, "GET", body["audio_url"])
    assert speeds == [voice_mode.SPEEDS["lambat"]] and voice_mode.usage()["answer"] == 1


def test_status_clip_is_made_once_then_served_from_disk(server, monkeypatch):  # noqa: F811
    loud = array("h", [0] * 3200 + [8000, -8000] * 1600 + [0] * 3200).tobytes()
    made = []

    def synthesize_part(text, previous_text=None, next_text=None, speed=None):
        made.append((text, speed))
        return loud

    monkeypatch.setattr(clips.tts, "synthesize_part", synthesize_part)
    for _ in range(2):
        response, pcm = request(server, "GET", "/v1/voice/clip/no_speech")
        assert response.status == 200
        assert 0 < len(pcm) < len(loud)  # hening di awal & akhir dipangkas
    assert made == [(clips.CLIPS["no_speech"], voice_mode.speed_value())]
    assert request(server, "GET", "/v1/voice/clip/rahasia")[0].status == 404

    voice_mode.save(speed="cepat")  # kecepatan berubah: dibuat ulang, versi lama dihapus
    request(server, "GET", "/v1/voice/clip/no_speech")
    assert len(made) == 2 and len(list(clips.CLIPS_DIR.glob("no_speech-*.pcm"))) == 1


# --------------------------------- dashboard --------------------------------
def test_accessibility_counts_ocr_pages_and_spoken_audio(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard_data, "MARKDOWN_DIR", tmp_path)
    (tmp_path / "index.json").write_text(
        json.dumps(
            {
                "a.pdf": {"converter": "pymupdf4llm+ocr(13 hal)"},
                "b.pdf": {"converter": "pymupdf4llm+ocr(2 hal)"},
                "c.pptx": {"converter": "pptx-slide"},
            }
        )
    )
    voice_mode.save(enabled=True)
    voice_mode.record("alert")
    audit = {"bisa_didengar": 18, "pertemuan_bermateri": 24, "pertemuan_ocr": 5}
    data = dashboard_data._accessibility(audit, questions_30d=40)
    assert data == {
        "voice_mode": True,
        "speed": "normal",
        "listenable_meetings": 18,
        "meetings_with_material": 24,
        "ocr_pages": 15,
        "ocr_meetings": 5,
        "questions_30d": 40,
        "answers_spoken_30d": 0,
        "alerts_spoken_30d": 1,
    }
    assert dashboard_data.panel("voice")["speeds"] == list(voice_mode.SPEEDS)
