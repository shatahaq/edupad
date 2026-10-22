"""Mode bahasa EduPad: Indonesia / Inggris (voice/lang.py)."""

import pytest
from tests.test_latency import FakeMemory, fake_llm  # noqa: F401 - fixture
from tests.test_server import ask_json, fake_tts, request, server  # noqa: F401 - fixture
from tests.test_tts import FakeResponse, settings  # noqa: F401 - fixture

from edupad.agent import assistant, tools
from edupad.office import dashboard_data
from edupad.voice import clips, commands, intro, lang, stt, tts
from edupad.voice import mode as voice_mode


# ------------------------------- pengaturan --------------------------------
def test_default_indonesian_then_switch_and_reject_unknown():
    assert lang.load() == {"lang": "id"} and not lang.is_english()
    assert lang.save("en") == {"lang": "en"}
    assert lang.is_english() and lang.label() == "English"
    with pytest.raises(ValueError):
        lang.save("jp")
    assert lang.current() == "en"


def test_tool_accepts_names_and_reports_errors():
    assert tools.TOOLS["set_language"]("English")["bahasa"] == "English"
    assert lang.current() == "en"
    assert tools.TOOLS["set_language"]("indonesia")["bahasa"] == "Indonesia"
    assert "error" in tools.TOOLS["set_language"]("klingon")


def test_pick_falls_back_to_indonesian_when_untranslated():
    lang.save("en")
    assert lang.pick({"id": "Halo", "en": "Hi"}) == "Hi"
    assert lang.pick({"id": "Halo"}) == "Halo"


# --------------------------------- perintah ---------------------------------
@pytest.mark.parametrize(
    "spoken",
    ["switch to English", "ganti ke bahasa Inggris", "speak english please", "english mode"],
)
def test_english_command_switches_without_llm(spoken):
    reply = commands.handle(spoken)
    assert reply["reply"] == "english" and lang.current() == "en"
    assert reply["speech"].startswith("English mode is on")  # konfirmasi dalam bahasa baru
    assert reply["audio_url"].startswith(commands.URL_PREFIX + "english")


@pytest.mark.parametrize("spoken", ["ganti ke bahasa Indonesia", "switch to Indonesian"])
def test_indonesian_command_switches_back(spoken):
    lang.save("en")
    reply = commands.handle(spoken)
    assert reply["reply"] == "indonesian" and lang.current() == "id"
    assert reply["speech"].startswith("Bahasa Indonesia aktif kembali")


def test_english_voice_mode_and_speed_commands():
    assert commands.handle("turn on voice mode")["reply"] == "on" and voice_mode.enabled()
    lang.save("en")
    assert commands.handle("speak faster")["reply"] == "cepat"
    assert commands.handle("turn off voice mode")["speech"].startswith("Voice mode is off")
    assert not voice_mode.enabled()


def test_questions_about_language_still_go_to_the_agent():
    assert commands.handle("kenapa bahasa Inggris susah?") is None
    assert commands.handle("apa bahasa Inggris dari pertemuan?") is None
    assert lang.current() == "id"


# ---------------------------- kalimat tetap & suara --------------------------
def test_clip_texts_and_urls_follow_language():
    assert clips.text("ready").startswith("EduPad siap")
    indonesian = clips.urls()
    lang.save("en")
    assert clips.text("ready") == "EduPad is ready. Hold the button, then just ask."
    assert set(clips.urls()) == set(indonesian) and clips.urls() != indonesian


def test_both_languages_stay_cached_when_switching(monkeypatch):
    made = []
    monkeypatch.setattr(
        clips.tts, "synthesize_part", lambda text, speed=None: made.append(text) or b"\x01\x00"
    )
    monkeypatch.setattr(clips.intro, "trim", lambda pcm: pcm)
    clips.load("ready")
    lang.save("en")
    clips.load("ready")
    clips.load("ready")  # dari simpanan
    lang.save("id")
    clips.load("ready")  # suara bahasa Indonesia tidak dibuang saat berganti bahasa
    assert len(made) == 2 and len(list(clips.CLIPS_DIR.glob("ready-*.pcm"))) == 2


def test_intro_script_and_cache_file_per_language(monkeypatch, tmp_path):
    monkeypatch.setattr(intro, "INTRO_DIR", tmp_path / "intro")
    monkeypatch.setattr(intro.tts, "synthesize_part", lambda text, **kwargs: b"\x01\x00" * 8000)
    assert intro.script()[0][1] == "Halo! Aku EduPad."
    intro.load()
    lang.save("en")
    meta, _ = intro.load()
    assert meta["lang"] == "en" and meta["segments"][0]["text"] == "Hi! I'm EduPad."
    assert (tmp_path / "intro" / "intro.pcm").exists()  # bahasa Indonesia tetap tersimpan
    assert (tmp_path / "intro" / "intro-en.pcm").exists()


def test_tts_and_stt_send_the_active_language(monkeypatch, settings):  # noqa: F811
    calls = []
    monkeypatch.setattr(tts.http_pool, "post", lambda url, **kw: calls.append(kw) or FakeResponse())
    lang.save("en")
    b"".join(tts.stream("Ready to study?"))
    assert calls[0]["json"]["language_code"] == "en"
    assert "assignment" in stt.vocabulary_prompt()
    lang.save("id")
    b"".join(tts.stream("Siap belajar?"))
    assert calls[1]["json"]["language_code"] == "id"
    assert "tugas" in stt.vocabulary_prompt()


# ----------------------------------- agent ----------------------------------
def test_prompt_adds_english_rules_only_in_english(monkeypatch):
    monkeypatch.setattr(assistant, "course_overview", lambda: "-")
    indonesian = assistant._system_prompt()
    assert "set_language" in indonesian and "ENGLISH MODE" not in indonesian
    lang.save("en")
    english = assistant._system_prompt()
    assert "ENGLISH MODE" in english and english.startswith(indonesian[:200])


def test_ask_sends_english_rules_after_switching(fake_llm, monkeypatch):  # noqa: F811
    monkeypatch.setattr(assistant, "course_overview", lambda: "-")
    assistant.ask("halo", memory=FakeMemory([]))
    lang.save("en")
    assistant.ask("hello again", memory=FakeMemory([]))
    first, second = (messages[0]["content"] for messages in fake_llm)
    assert "ENGLISH MODE" not in first and "ENGLISH MODE" in second


# --------------------------------- dashboard --------------------------------
def test_settings_panel_reports_language():
    panel = dashboard_data.voice_panel()
    assert panel["lang"] == "id" and panel["languages"] == {"id": "Indonesia", "en": "English"}
    lang.save("en")
    assert dashboard_data.voice_panel()["lang"] == "en"


# --------------------------------- perangkat --------------------------------
def test_device_gets_language_and_switches_by_voice(server, fake_tts):  # noqa: F811
    status, body = ask_json(server, "switch to English")
    assert status == 200 and server.asked == [] and fake_tts == []  # tanpa LLM & kuota TTS
    assert body["language"] == "en" and body["speech"].startswith("English mode is on")
    assert body["audio_url"].startswith("/v1/voice/reply/english?v=")
    assert ask_json(server, "ganti ke bahasa Indonesia")[1]["language"] == "id"
