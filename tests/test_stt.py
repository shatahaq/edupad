import math
import struct
from dataclasses import replace

import pytest

from edupad import cli
from edupad.config import get_settings
from edupad.voice import stt, tts


class FakeResponse:
    def __init__(self, status=200, body=None, text=""):
        self.status_code, self.ok = status, status < 400
        self.body, self.text = body if body is not None else {"text": " Pertemuan 5 PV? "}, text

    def json(self):
        if self.body is ValueError:
            raise ValueError("bukan JSON")
        return self.body


def tone(seconds, amplitude=8000):
    """Sinus 440 Hz; amplitudo 8000 ~ -12 dBFS (ucapan), 100 ~ -50 dBFS (derau)."""
    n = int(stt.SAMPLE_RATE * seconds)
    return b"".join(
        struct.pack("<h", int(amplitude * math.sin(2 * math.pi * 440 * i / stt.SAMPLE_RATE)))
        for i in range(n)
    )


@pytest.fixture
def settings(monkeypatch):
    base = replace(
        get_settings(),
        stt_provider="groq",
        stt_model="whisper-large-v3-turbo",
        groq_api_key="gsk_test",
    )
    monkeypatch.setattr(stt, "get_settings", lambda: base)
    monkeypatch.setattr(
        stt,
        "read_json",
        lambda path: {
            "mata_kuliah": [
                {"matkul": "Pemrograman Visual", "alias": ["pemrograman visual", "pv", "tif3031"]},
                {"matkul": "Praktikum Pemrograman Visual", "alias": ["prak pv", "praktikum pv"]},
                {"matkul": "Manajemen Sistem Basis Data", "alias": ["msbd"]},
            ]
        },
    )
    return base


def test_transcribe_pcm_sends_wav_with_model_language_and_vocabulary(monkeypatch, settings):
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse()

    monkeypatch.setattr(stt.http_pool, "post", fake_post)
    assert stt.transcribe_pcm(tone(1)) == "Pertemuan 5 PV?"
    url, kwargs = calls[0]
    assert url == "https://api.groq.com/openai/v1/audio/transcriptions"
    assert kwargs["headers"] == {"Authorization": "Bearer gsk_test"}
    name, audio = kwargs["files"]["file"]
    assert name == "audio.wav" and audio[:4] == b"RIFF" and audio[8:12] == b"WAVE"
    data = kwargs["data"]
    assert (data["model"], data["language"], data["response_format"]) == (
        "whisper-large-v3-turbo",
        "id",
        "json",
    )
    assert data["prompt"] == (
        "EduPad, jadwal kuliah, tugas, deadline, pertemuan, presensi, "
        "Pemrograman Visual, Manajemen Sistem Basis Data, PV, MSBD."
    )


def test_file_keeps_its_name_and_punctuation_only_is_empty(monkeypatch, settings):
    calls = []
    monkeypatch.setattr(
        stt.http_pool,
        "post",
        lambda url, **kw: calls.append(kw) or FakeResponse(body={"text": " . "}),
    )
    assert stt.transcribe(b"ID3...", "tanya.mp3") == ""
    assert calls[0]["files"]["file"] == ("tanya.mp3", b"ID3...")


def test_silence_noise_and_short_audio_do_not_call_provider(monkeypatch, settings):
    monkeypatch.setattr(stt.http_pool, "post", lambda *a, **k: pytest.fail("provider dipanggil"))
    assert stt.transcribe_pcm(b"\x00\x00" * stt.SAMPLE_RATE * 2) == ""
    assert stt.transcribe_pcm(tone(2, amplitude=100)) == ""
    assert stt.transcribe_pcm(tone(0.2)) == ""
    assert stt.transcribe_pcm(tone(0.1) + b"\x00\x00" * stt.SAMPLE_RATE) == ""  # bunyi < 0,25 s
    assert stt.transcribe(b"") == ""
    with pytest.raises(stt.STTError, match="melebihi"):
        stt.transcribe_pcm(b"\x00\x00" * stt.SAMPLE_RATE * (stt.MAX_SECONDS + 1))
    with pytest.raises(stt.STTError, match="melebihi"):
        stt.transcribe(b"\x00" * (stt.MAX_FILE_BYTES + 1))


def test_has_speech_ignores_odd_trailing_byte():
    assert stt.has_speech(tone(0.5) + b"\x01")
    assert not stt.has_speech(b"\x00\x00" * 8000 + b"\x01")


def test_error_message_from_provider(monkeypatch, settings):
    body = {"error": {"message": "Invalid API Key", "type": "invalid_request_error"}}
    monkeypatch.setattr(
        stt.http_pool, "post", lambda url, **kw: FakeResponse(status=401, body=body)
    )
    with pytest.raises(stt.STTError, match="401.*Invalid API Key"):
        stt.transcribe_pcm(tone(1))
    monkeypatch.setattr(
        stt.http_pool,
        "post",
        lambda url, **kw: FakeResponse(status=502, body=ValueError, text="Bad Gateway"),
    )
    with pytest.raises(stt.STTError, match="502.*Bad Gateway"):
        stt.transcribe_pcm(tone(1))


def test_connection_error_is_stt_error(monkeypatch, settings):
    def broken(url, **kw):
        raise stt.requests.exceptions.ConnectionError("Name or service not known")

    monkeypatch.setattr(stt.http_pool, "post", broken)
    with pytest.raises(stt.STTError, match="tidak bisa dihubungi"):
        stt.transcribe_pcm(tone(1))


def test_missing_key_and_unknown_provider(monkeypatch, settings):
    monkeypatch.setattr(stt, "get_settings", lambda: replace(settings, groq_api_key=None))
    with pytest.raises(stt.STTError, match="belum diisi"):
        stt.transcribe_pcm(tone(1))
    monkeypatch.setattr(stt, "get_settings", lambda: replace(settings, stt_provider="lain"))
    with pytest.raises(stt.STTError, match="tidak dikenal"):
        stt.transcribe_pcm(tone(1))


@pytest.fixture
def routed(monkeypatch):
    asked = []
    monkeypatch.setattr(cli, "setup_logging", lambda _: None)
    monkeypatch.setattr(cli, "_ask", lambda question, *a: asked.append((question, *a)) or 0)
    return asked


def test_ask_audio_asks_the_transcript(monkeypatch, routed):
    monkeypatch.setattr(cli, "_listen", lambda path: f"isi {path}")
    assert cli.main(["ask", "--audio", "tanya.wav", "--speak", "--new"]) == 0
    assert routed == [("isi tanya.wav", False, False, True, True, True)]


def test_ask_text_is_unchanged(monkeypatch, routed):
    monkeypatch.setattr(cli, "_listen", lambda path: pytest.fail("STT dipanggil"))
    assert cli.main(["ask", "PV pertemuan 5 tentang apa?", "--trace"]) == 0
    assert routed == [("PV pertemuan 5 tentang apa?", True, False, False, True, False)]


def test_ask_audio_without_speech_or_failed_stt_does_not_ask(monkeypatch, routed):
    for heard in ("", None):
        monkeypatch.setattr(cli, "_listen", lambda path, heard=heard: heard)
        assert cli.main(["ask", "--audio", "tanya.wav"]) == 1
    assert routed == []


def test_ask_needs_exactly_one_of_question_or_audio(routed):
    for argv in (["ask"], ["ask", "halo", "--audio", "tanya.wav"]):
        with pytest.raises(SystemExit):
            cli.main(argv)
    assert routed == []


def test_listen_routes_device_wav_to_pcm_and_other_files_as_is(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(stt, "transcribe_pcm", lambda pcm: calls.append(("pcm", pcm)) or "a")
    monkeypatch.setattr(stt, "transcribe", lambda audio, name: calls.append((name, audio)) or "b")
    device, mp3 = tmp_path / "rekaman.wav", tmp_path / "tanya.mp3"
    device.write_bytes(tts.to_wav(b"\x01\x00" * 4))
    mp3.write_bytes(b"ID3...")
    assert (cli._listen(str(device)), cli._listen(str(mp3))) == ("a", "b")
    assert calls == [("pcm", b"\x01\x00" * 4), ("tanya.mp3", b"ID3...")]
    assert cli._listen(str(tmp_path / "tidak_ada.wav")) is None
