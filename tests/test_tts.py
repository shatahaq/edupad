import io
import threading
import time
import wave
from dataclasses import replace

import pytest

from edupad import config
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
    base = replace(
        get_settings(),
        tts_provider="elevenlabs",
        tts_model="eleven_multilingual_v2",
        elevenlabs_api_key="key",
        elevenlabs_voice_id="voice123",
        elevenlabs_accounts=(("key", "voice123"),),  # .env asli tidak ikut terpakai saat tes
    )
    monkeypatch.setattr(tts, "get_settings", lambda: base)
    tts._blocked.clear()  # akun yang dilewati tidak bocor antar tes
    return base


def test_stream_requests_pcm_16k_with_voice_and_model(monkeypatch, settings):
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse()

    monkeypatch.setattr(tts.http_pool, "post", fake_post)
    pcm = tts.synthesize("  Halo,   aku EduPad. ")
    url, kwargs = calls[0]
    assert url.endswith("/text-to-speech/voice123/stream")
    assert kwargs["params"] == {"output_format": "pcm_16000"}
    assert kwargs["json"] == {
        "text": "Halo, aku EduPad.",
        "model_id": "eleven_multilingual_v2",
        "language_code": "id",
        "voice_settings": tts.VOICE_SETTINGS,
        "seed": tts.SEED,
    }
    assert kwargs["headers"] == {"xi-api-key": "key"} and kwargs["stream"]
    assert len(pcm) == 3200 and tts.duration_seconds(pcm) == 0.1


def test_error_message_from_provider(monkeypatch, settings):
    body = {"detail": {"message": "Free users cannot use library voices via the API."}}
    monkeypatch.setattr(
        tts.http_pool, "post", lambda url, **kw: FakeResponse(status=402, body=body)
    )
    with pytest.raises(tts.TTSError, match="402.*library voices"):
        tts.synthesize("halo")


def test_connection_drop_mid_stream_is_tts_error(monkeypatch, settings):
    class BrokenResponse(FakeResponse):
        def iter_content(self, size):
            yield b"\x01\x00" * 800
            raise tts.requests.exceptions.ChunkedEncodingError("Connection broken")

    monkeypatch.setattr(tts.http_pool, "post", lambda url, **kw: BrokenResponse())
    with pytest.raises(tts.TTSError, match="terputus.*Connection broken"):
        tts.synthesize("halo")


def test_missing_keys_and_unknown_provider(monkeypatch, settings):
    monkeypatch.setattr(tts, "get_settings", lambda: replace(settings, elevenlabs_accounts=()))
    with pytest.raises(tts.TTSError, match="belum diisi"):
        tts.synthesize("halo")
    monkeypatch.setattr(tts, "get_settings", lambda: replace(settings, tts_provider="lain"))
    with pytest.raises(tts.TTSError, match="tidak dikenal"):
        tts.synthesize("halo")


def test_empty_and_too_long_text_do_not_call_provider(monkeypatch, settings):
    monkeypatch.setattr(tts.http_pool, "post", lambda *a, **k: pytest.fail("provider dipanggil"))
    assert tts.synthesize("   ") == b""
    with pytest.raises(tts.TTSError, match="melebihi"):
        tts.synthesize("a" * (tts.MAX_TEXT_CHARS + 1))


def test_wav_header_matches_esp32_format():
    data = tts.to_wav(b"\x00\x00" * 16000)
    with wave.open(io.BytesIO(data)) as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()) == (
            1,
            2,
            16000,
            16000,
        )


LONG = (
    "Pertemuan lima Pemrograman Visual membahas percabangan If-Else, yaitu cara program "
    "mengambil keputusan. Di situ dibahas If Then, ElseIf, sampai Nested If, plus operator "
    "logika And, Or, Not. Ada juga studi kasus diskon pemesanan makanan."
)
FIRST, REST = LONG[: LONG.index(". ") + 1], LONG[LONG.index(". ") + 2 :]


def test_split_first_sentence_only_when_it_helps():
    assert tts.split_first(LONG) == [FIRST, REST]
    assert tts.split_first("Halo, aku EduPad.") == ["Halo, aku EduPad."]
    assert tts.split_first("Oke. " + LONG)[0] == "Oke. " + FIRST  # kalimat terlalu pendek digabung
    assert tts.split_first("Nilai 3.5 " + "a" * 150) == [
        "Nilai 3.5 " + "a" * 150
    ]  # bukan akhir kalimat
    assert tts.split_first("a" * 230 + ". " + "b" * 50) == ["a" * 230 + ". " + "b" * 50]


@pytest.fixture
def fake_provider(monkeypatch, settings):
    calls, state = [], {"active": 0, "peak": 0, "fail_rest_once": False}
    lock = threading.Lock()

    def provider(text, delay=0.01, **context):
        calls.append((text, context))
        with lock:
            state["active"] += 1
            state["peak"] = max(state["peak"], state["active"])
        try:
            if state["fail_rest_once"] and "previous_text" in context:
                state["fail_rest_once"] = False
                raise tts.TTSError("ElevenLabs HTTP 429: too_many_concurrent_requests", 429)
            for i in range(5):
                time.sleep(delay)
                yield text[:2].encode() + bytes([i])
        finally:
            with lock:
                state["active"] -= 1

    monkeypatch.setitem(tts.PROVIDERS, "elevenlabs", provider)
    return calls, state


def test_long_answer_streams_first_sentence_then_rest_with_context(fake_provider):
    calls, _ = fake_provider
    chunks = list(tts.stream(LONG))
    assert chunks == [FIRST[:2].encode() + bytes([i]) for i in range(5)] + [
        REST[:2].encode() + bytes([i]) for i in range(5)
    ]
    assert sorted(calls) == sorted([(FIRST, {"next_text": REST}), (REST, {"previous_text": FIRST})])


def test_rest_is_synthesized_while_first_part_plays(fake_provider):
    calls, _ = fake_provider
    audio = tts.stream(LONG)
    next(audio)  # perangkat baru menerima potongan pertama
    deadline = time.time() + 2
    while len(calls) < 2 and time.time() < deadline:
        time.sleep(0.01)
    assert len(calls) == 2
    audio.close()


def test_never_more_than_two_parallel_requests(fake_provider):
    _, state = fake_provider
    results = []
    threads = [
        threading.Thread(target=lambda: results.append(tts.synthesize(LONG))) for _ in range(3)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert state["peak"] <= tts.MAX_CONCURRENT and len(set(results)) == 1 and len(results[0]) == 30


def test_rest_retries_once_after_429(fake_provider):
    calls, state = fake_provider
    state["fail_rest_once"] = True
    assert len(tts.synthesize(LONG)) == 30
    assert [text for text, _ in calls].count(REST) == 2


def test_error_in_first_part_raises_before_any_audio(monkeypatch, settings):
    def provider(text, **context):
        raise tts.TTSError("ElevenLabs HTTP 401: invalid_api_key", 401)
        yield

    monkeypatch.setitem(tts.PROVIDERS, "elevenlabs", provider)
    with pytest.raises(tts.TTSError, match="invalid_api_key"):
        next(tts.stream(LONG))


def test_stopping_early_does_not_spend_quota_on_waiting_part(fake_provider, monkeypatch):
    calls, _ = fake_provider
    monkeypatch.setattr(tts, "_SLOTS", threading.BoundedSemaphore(1))  # bagian kedua harus menunggu
    audio = tts.stream(LONG)
    next(audio)
    audio.close()
    time.sleep(0.3)
    assert [text for text, _ in calls] == [FIRST]


def test_split_payload_carries_context_to_elevenlabs(monkeypatch, settings):
    sent = []
    monkeypatch.setattr(
        tts.http_pool, "post", lambda url, **kw: sent.append(kw["json"]) or FakeResponse()
    )
    tts.synthesize(LONG)
    by_text = {p["text"]: p for p in sent}
    assert by_text[FIRST]["next_text"] == REST and "previous_text" not in by_text[FIRST]
    assert by_text[REST]["previous_text"] == FIRST and "next_text" not in by_text[REST]
    assert all(p["seed"] == tts.SEED and p["model_id"] == "eleven_multilingual_v2" for p in sent)


# ----------------------- beberapa akun ElevenLabs ---------------------------
QUOTA = {"detail": {"status": "quota_exceeded", "message": "You have 12 credits remaining"}}


@pytest.fixture
def two_accounts(monkeypatch, settings):
    monkeypatch.setattr(
        tts,
        "get_settings",
        lambda: replace(settings, elevenlabs_accounts=(("key1", "voice1"), ("key2", "voice2"))),
    )


def _posts(monkeypatch, *responses):
    """Rekam tiap permintaan; `responses` dipakai berurutan, yang terakhir untuk sisanya."""
    calls = []
    answers = list(responses)

    def fake_post(url, **kwargs):
        calls.append((url, kwargs["headers"]["xi-api-key"]))
        return answers.pop(0) if len(answers) > 1 else answers[0]

    monkeypatch.setattr(tts.http_pool, "post", fake_post)
    return calls


def test_exhausted_account_moves_to_the_next_one(monkeypatch, two_accounts):
    calls = _posts(monkeypatch, FakeResponse(401, body=QUOTA), FakeResponse())
    assert tts.synthesize("halo") == b"\x01\x00" * 800 + b"\x02\x00" * 800
    assert [key for _, key in calls] == ["key1", "key2"]
    assert calls[1][0].endswith("/text-to-speech/voice2/stream")  # voice akun kedua


def test_exhausted_account_is_skipped_on_the_next_request(monkeypatch, two_accounts):
    calls = _posts(monkeypatch, FakeResponse(401, body=QUOTA), FakeResponse())
    tts.synthesize("halo")
    tts.synthesize("halo lagi")
    assert [key for _, key in calls] == ["key1", "key2", "key2"]  # akun habis tidak dicoba lagi


def test_all_accounts_exhausted_reports_the_last_error(monkeypatch, two_accounts):
    _posts(monkeypatch, FakeResponse(401, body=QUOTA))
    with pytest.raises(tts.TTSError, match="credits remaining"):
        tts.synthesize("halo")
    assert tts.accounts()[0][0] == "key1"  # semua dilewati: urutan .env dicoba lagi


def test_wrong_voice_id_is_not_treated_as_quota(monkeypatch, two_accounts):
    detail = {"detail": {"status": "voice_not_found", "message": "A voice with voice_id ..."}}
    calls = _posts(monkeypatch, FakeResponse(404, body=detail), FakeResponse())
    with pytest.raises(tts.TTSError, match="HTTP 404"):
        tts.synthesize("halo")
    assert [key for _, key in calls] == ["key1"]  # salah isi .env harus kelihatan, bukan ditutupi


def test_second_voice_id_defaults_to_the_first(monkeypatch):
    monkeypatch.setenv("API_KEY_ElevenLabs", "key1")
    monkeypatch.setenv("Voice_ID_ElevenLabs", "voice1")
    monkeypatch.setenv("API_KEY_ElevenLabs2", "key2")
    monkeypatch.delenv("Voice_ID_ElevenLabs2", raising=False)
    monkeypatch.setenv("API_KEY_ElevenLabs4", "key4")
    monkeypatch.setenv("Voice_ID_ElevenLabs4", "voice4")
    assert config.elevenlabs_accounts() == (
        ("key1", "voice1"),
        ("key2", "voice1"),  # voice kosong = ikut akun pertama (hanya cocok untuk suara bawaan)
        ("key4", "voice4"),  # nomor yang bolong dilewati
    )
