import json

import pytest

from edupad.voice import intro, tts

LOUD, QUIET = b"\x10\x27", b"\x00\x00"  # 10000 dan 0


@pytest.fixture
def fake_tts(monkeypatch, tmp_path):
    calls = []

    def synthesize_part(text, previous_text=None, next_text=None):
        calls.append((text, previous_text, next_text))
        return QUIET * 3200 + LOUD * 8000 + QUIET * 3200  # 0,2 s hening, 0,5 s suara, 0,2 s hening

    monkeypatch.setattr(intro.tts, "synthesize_part", synthesize_part)
    monkeypatch.setattr(intro, "INTRO_DIR", tmp_path / "intro")
    monkeypatch.setattr(
        intro, "SCRIPT", [("wave", "Halo!"), ("book", "Materi."), ("cheer", "Yuk!")]
    )
    return calls


def test_trim_keeps_short_edge_around_speech():
    edge = int(intro.EDGE_SECONDS * tts.SAMPLE_RATE)
    pcm = QUIET * 4000 + LOUD * 100 + QUIET * 4000
    assert intro.trim(pcm) == QUIET * edge + LOUD * 100 + QUIET * edge
    assert intro.trim(QUIET * 100) == b""


def test_segments_start_where_each_sentence_starts(fake_tts):
    meta, pcm = intro.load()
    sentence = 2 * (8000 + 2 * int(intro.EDGE_SECONDS * tts.SAMPLE_RATE))
    gap = 2 * int(intro.GAP_SECONDS * tts.SAMPLE_RATE)
    assert len(pcm) == 3 * sentence + 2 * gap
    assert [s["start"] for s in meta["segments"]] == [
        0,
        round((sentence + gap) / intro.BYTES_PER_SECOND, 3),
        round(2 * (sentence + gap) / intro.BYTES_PER_SECOND, 3),
    ]
    assert [s["gesture"] for s in meta["segments"]] == ["wave", "book", "cheer"]
    assert meta["duration"] == round(len(pcm) / intro.BYTES_PER_SECOND, 3)
    # kalimat tetangga dikirim sebagai konteks intonasi
    assert fake_tts[1] == ("Materi.", "Halo!", "Yuk!")


def test_saved_once_then_reused_until_script_changes(fake_tts, monkeypatch):
    first = intro.load()
    assert intro.load() == first and len(fake_tts) == 3  # dari simpanan, tanpa TTS
    saved = json.loads((intro.INTRO_DIR / "intro.json").read_text())
    assert saved["version"] == first[0]["version"]

    monkeypatch.setattr(intro, "SCRIPT", [("wave", "Halo lagi!")])
    meta, _ = intro.load()
    assert len(fake_tts) == 4 and meta["segments"][0]["text"] == "Halo lagi!"
    assert intro.load(regenerate=True) and len(fake_tts) == 5


def test_failed_tts_keeps_previous_audio(fake_tts, monkeypatch):
    before = intro.load()

    def broken(*args, **kwargs):
        raise tts.TTSError("kuota habis")

    monkeypatch.setattr(intro.tts, "synthesize_part", broken)
    with pytest.raises(tts.TTSError):
        intro.load(regenerate=True)
    assert (intro.INTRO_DIR / "intro.pcm").read_bytes() == before[1]
