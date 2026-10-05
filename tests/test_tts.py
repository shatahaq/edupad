import io
import wave
from dataclasses import replace

import pytest

from edupad.config import get_settings
from edupad.voice import tts


class FakeResponse:
    def __init__(self, status=200, chunks=(b"\x01\x00" * 800, b"\x02\x00" * 800), body=None):
        self.status_code, self.ok = status, status < 400
        self.chunks, self.body, self.text = chunks, body or {}, ""

    def iter_content(self, size):
        yield from self.chunks

    def json(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def settings(monkeypatch):
    base = replace(get_settings(), tts_provider="elevenlabs", tts_model="eleven_multilingual_v2",
                   elevenlabs_api_key="key", elevenlabs_voice_id="voice123")
    monkeypatch.setattr(tts, "get_settings", lambda: base)
    return base


def test_stream_requests_pcm_16k_with_voice_and_model(monkeypatch, settings):
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse()

    monkeypatch.setattr(tts.requests, "post", fake_post)
    pcm = tts.synthesize("  Halo,   aku EduPad. ")
    url, kwargs = calls[0]
    assert url.endswith("/text-to-speech/voice123/stream")
    assert kwargs["params"] == {"output_format": "pcm_16000"}
    assert kwargs["json"] == {"text": "Halo, aku EduPad.", "model_id": "eleven_multilingual_v2",
                              "language_code": "id", "voice_settings": tts.VOICE_SETTINGS,
                              "seed": tts.SEED}
    assert kwargs["headers"] == {"xi-api-key": "key"} and kwargs["stream"]
    assert len(pcm) == 3200 and tts.duration_seconds(pcm) == 0.1


def test_error_message_from_provider(monkeypatch, settings):
    body = {"detail": {"message": "Free users cannot use library voices via the API."}}
    monkeypatch.setattr(tts.requests, "post", lambda url, **kw: FakeResponse(status=402, body=body))
    with pytest.raises(tts.TTSError, match="402.*library voices"):
        tts.synthesize("halo")


def test_missing_keys_and_unknown_provider(monkeypatch, settings):
    monkeypatch.setattr(tts, "get_settings", lambda: replace(settings, elevenlabs_api_key=None))
    with pytest.raises(tts.TTSError, match="belum diisi"):
        tts.synthesize("halo")
    monkeypatch.setattr(tts, "get_settings", lambda: replace(settings, tts_provider="lain"))
    with pytest.raises(tts.TTSError, match="tidak dikenal"):
        tts.synthesize("halo")


def test_empty_and_too_long_text_do_not_call_provider(monkeypatch, settings):
    monkeypatch.setattr(tts.requests, "post", lambda *a, **k: pytest.fail("provider dipanggil"))
    assert tts.synthesize("   ") == b""
    with pytest.raises(tts.TTSError, match="melebihi"):
        tts.synthesize("a" * (tts.MAX_TEXT_CHARS + 1))


def test_wav_header_matches_esp32_format():
    data = tts.to_wav(b"\x00\x00" * 16000)
    with wave.open(io.BytesIO(data)) as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()) == (1, 2, 16000, 16000)
