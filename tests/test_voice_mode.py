"""Mode Suara: EduPad dipakai tanpa melihat layar (voice/mode.py, voice/clips.py)."""

import json
from array import array

import pytest
from tests.test_latency import FakeMemory, fake_llm  # noqa: F401 - fixture
from tests.test_server import ask_json, fake_tts, request, server  # noqa: F401 - fixture

from edupad.agent import assistant, tools
from edupad.agent.formatting import MAX_SPEECH_CHARS, VOICE_MODE_SPEECH_CHARS
from edupad.office import dashboard_data
from edupad.voice import clips, commands
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
REVIEW = {  # jenis yang hanya dibacakan saat Mode Suara aktif
    "id": "rev:msbd",
    "kind": "review",
    "course": "Prak MSBD",
    "detail": "Normalisasi",
    "when": "Penguasaan 40%",
    "from_ts": 0,
    "to_ts": 0,
    "speech": "Waktunya mengulang normalisasi di praktikum MSBD.",
}


@pytest.fixture
def device_updates(monkeypatch):
    from edupad import server as srv

    monkeypatch.setattr(
        srv.updates,
        "updates",
        lambda extra_cards=False: {
            "now_ts": 1,
            "next_class": None,
            "alerts": [dict(ALERT), dict(REVIEW)],
        },
    )


def _updates(server):  # noqa: F811
    response, data = request(server, "GET", "/v1/updates", headers={"X-Firmware": "1.2"})
    assert response.status == 200
    return json.loads(data)


def test_deadline_is_spoken_but_review_is_not_when_mode_is_off(server, device_updates):  # noqa: F811
    body = _updates(server)
    assert body["voice_mode"] is False and "voice_clips" not in body
    assert body["alerts"][0]["audio_url"].startswith("/v1/speech/")  # deadline tugas
    assert "audio_url" not in body["alerts"][1]  # kartu review: hanya di Mode Suara


def test_alert_is_spoken_once_and_cached(server, device_updates, fake_tts):  # noqa: F811
    voice_mode.save(enabled=True, speed="cepat")
    body = _updates(server)
    assert body["voice_mode"] is True
    assert body["voice_clips"]["wifi"].startswith("/v1/voice/clip/wifi?v=")
    url = body["alerts"][0]["audio_url"]
    assert url == _updates(server)["alerts"][0]["audio_url"]  # pemberitahuan sama, kunci sama
    assert "audio_url" in body["alerts"][1]  # mode aktif: semua jenis ikut dibacakan

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
    assert made == [(clips.text("no_speech"), voice_mode.speed_value())]
    assert request(server, "GET", "/v1/voice/clip/rahasia")[0].status == 404

    voice_mode.save(speed="cepat")  # kecepatan berubah: dibuat untuk kecepatan itu
    request(server, "GET", "/v1/voice/clip/no_speech")
    assert len(made) == 2 and len(list(clips.CLIPS_DIR.glob("no_speech-*.pcm"))) == 2

    voice_mode.save(speed="normal")  # kembali: varian lama masih ada, TTS tidak dipakai lagi
    request(server, "GET", "/v1/voice/clip/no_speech")
    assert len(made) == 2

    monkeypatch.setitem(
        clips.CLIPS, "no_speech", {"id": "Teks baru.", "en": "New text."}
    )  # teks diubah: sisa lama dibuang
    request(server, "GET", "/v1/voice/clip/no_speech")
    assert made[-1][0] == "Teks baru."
    assert len(list(clips.CLIPS_DIR.glob("no_speech-*.pcm"))) == 1


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
        "language": "id",
        "listenable_meetings": 18,
        "meetings_with_material": 24,
        "ocr_pages": 15,
        "ocr_meetings": 5,
        "questions_30d": 40,
        "answers_spoken_30d": 0,
        "alerts_spoken_30d": 1,
    }
    assert dashboard_data.panel("voice")["speeds"] == list(voice_mode.SPEEDS)


# ------------------ perintah setelan: dijawab tanpa LLM & TTS ------------------
def test_only_settings_commands_are_matched():
    perintah = [
        "aktifkan mode suara",
        "Matikan mode suara.",
        "nyalain mode tunanetra",
        "tolong bicara lebih cepat",
        "bicara lebih lambat ya",
        "percepat bicaranya",
    ]
    pertanyaan = [  # diteruskan ke agent: pertanyaan, bukan perintah
        "mode suara",
        "apa itu mode suara?",
        "jelaskan lebih cepat",
        "kenapa mode suara tidak bisa dimatikan",
        "apa tugas minggu ini?",
    ]
    assert all(commands._match(t) for t in perintah)
    assert not any(commands._match(t) for t in pertanyaan)


def test_speed_moves_one_step_and_stops_at_the_end():
    voice_mode.save(speed="normal")
    assert [commands.handle("bicara lebih cepat")["reply"] for _ in range(3)] == [
        "cepat",
        "sangat_cepat",
        "fastest",
    ]
    assert voice_mode.load()["speed"] == "sangat_cepat"  # mentok, tidak melewati batas
    assert commands.handle("bicara lebih lambat")["reply"] == "cepat"


def test_settings_command_skips_agent_and_tts(server, fake_tts):  # noqa: F811
    status, body = ask_json(server, "aktifkan mode suara")
    assert status == 200 and voice_mode.load()["enabled"] is True
    assert server.asked == [] and fake_tts == []  # tanpa token LLM, tanpa kuota TTS
    assert body["speech"] == commands.reply("on")["speech"] and body["screen"]["lines"]
    assert body["audio_url"].startswith("/v1/voice/reply/on?v=")
    assert body["voice_mode"] is True and set(body["voice_clips"]) == set(clips.CLIPS)
    assert voice_mode.usage()["answer"] == 1


def test_question_about_voice_mode_still_reaches_the_agent(server, fake_tts):  # noqa: F811
    ask_json(server, "apa itu mode suara?")
    assert [q for q, _ in server.asked] == ["apa itu mode suara?"]


def test_template_audio_is_made_once_then_served_from_disk(server, monkeypatch):  # noqa: F811
    loud = array("h", [0] * 3200 + [8000, -8000] * 1600 + [0] * 3200).tobytes()
    made = []

    def synthesize_part(text, previous_text=None, next_text=None, speed=None):
        made.append((text, speed))
        return loud

    monkeypatch.setattr(clips.tts, "synthesize_part", synthesize_part)
    for _ in range(2):
        response, pcm = request(server, "GET", "/v1/voice/reply/on")
        assert response.status == 200 and 0 < len(pcm) < len(loud)
    assert made == [(commands.reply("on")["speech"], voice_mode.speed_value())]
    assert request(server, "GET", "/v1/voice/reply/rahasia")[0].status == 404


def test_toggle_audio_is_reused_across_speeds(server, monkeypatch):  # noqa: F811
    """Tiap (kalimat, kecepatan) dibuat sekali; bolak-balik setelah itu gratis."""
    made = []
    monkeypatch.setattr(
        clips.tts,
        "synthesize_part",
        lambda text, previous_text=None, next_text=None, speed=None: (
            made.append(speed) or b"\0" * 64000
        ),
    )
    monkeypatch.setattr(clips.intro, "trim", lambda pcm: pcm)

    def say(text):
        request(server, "GET", ask_json(server, text)[1]["audio_url"])

    voice_mode.save(speed="normal")
    for text in ("aktifkan mode suara", "matikan mode suara", "aktifkan mode suara"):
        say(text)
    assert len(made) == 2  # 'aktifkan' kedua sudah dari simpanan

    say("bicara lebih cepat")  # -> kalimat 'cepat', selalu diucapkan pada kecepatan cepat
    say("bicara lebih lambat")  # -> kalimat 'normal', kalimat yang lain lagi
    say("bicara lebih cepat")  # -> 'cepat' lagi: sudah ada
    assert len(made) == 4

    at_normal = len(made)
    for _ in range(3):  # aktif/mati di kecepatan 'cepat': sekali saja per kalimat
        say("matikan mode suara")
        say("aktifkan mode suara")
    assert len(made) == at_normal + 2
