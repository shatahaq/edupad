"""Buat suara TTS asli untuk `make video`: perkenalan dan satu jawaban contoh.

python make_voice.py [voice_dir] [--force]

Dijalankan dengan paket edupad (root repo, .env berisi API_KEY_ElevenLabs/Voice_ID_ElevenLabs),
mis. dari Windows: `python firmware/preview/new_ui_preview/make_voice.py`. Hasil di voice_dir
(bawaan: voice/ di sebelah file ini):
  intro.pcm, intro.tsv  suara perkenalan + start<TAB>gesture<TAB>teks per kalimat
                        (dibuat seperti voice/intro.py di server: per kalimat, dipangkas, jeda 0,2 s)
  answer.pcm            suara jawaban layar "answer" di preview.cpp (tts.synthesize, jalur asli)
Semua PCM 16-bit mono 16 kHz. Kuota TTS hanya terpakai bila naskah/suara berubah (lihat meta.json).
"""

from __future__ import annotations

import hashlib
import json
import sys
from array import array
from pathlib import Path

from edupad.agent.formatting import to_display_text
from edupad.config import get_settings
from edupad.voice import tts

# sama dengan SCRIPT di src/edupad/voice/intro.py (branch esp32-voice)
INTRO = [
    ("wave", "Halo! Aku EduPad."),
    ("happy", "Teman belajarmu."),
    ("book", "Aku bisa menjelaskan materi kuliahmu,"),
    ("tasks", "mengecek tugas, deadline, dan presensi."),
    ("button", "Caranya gampang: tahan tombol, lalu tanya saja."),
    ("cheer", "Yuk, mulai belajar!"),
]
# jawaban suara untuk layar "answer" (PV Pertemuan 5: If-Else) di preview.cpp
ANSWER = (
    "Di pertemuan lima Pemrograman Visual, kamu belajar percabangan If-Else, "
    "yaitu cara memilih aksi sesuai kondisi. Lalu ada ElseIf, Nested If, dan operator logika "
    "And, Or, Not. Latihannya membuat kalkulator nilai huruf pakai If-ElseIf."
)
GAP_SECONDS = 0.2
EDGE_SECONDS = 0.06
SILENCE = 500
BYTES_PER_SECOND = tts.SAMPLE_RATE * tts.SAMPLE_WIDTH


def trim(pcm: bytes) -> bytes:
    """Buang hening di awal/akhir (sisakan EDGE_SECONDS), seperti voice/intro.py."""
    samples = array("h", pcm[: len(pcm) - len(pcm) % tts.SAMPLE_WIDTH])
    loud = [i for i, v in enumerate(samples) if abs(v) > SILENCE]
    if not loud:
        return b""
    edge = int(EDGE_SECONDS * tts.SAMPLE_RATE)
    return samples[max(0, loud[0] - edge) : loud[-1] + 1 + edge].tobytes()


def part(text: str, previous_text: str | None, next_text: str | None) -> bytes:
    provider = tts.PROVIDERS[get_settings().tts_provider]
    return b"".join(provider(text, previous_text=previous_text, next_text=next_text))


def make_intro(out: Path) -> None:
    texts = [text for _, text in INTRO]
    gap = b"\0" * (int(GAP_SECONDS * tts.SAMPLE_RATE) * tts.SAMPLE_WIDTH)
    pcm, rows = b"", []
    for i, (gesture, text) in enumerate(INTRO):
        voice = trim(part(text, " ".join(texts[:i]) or None, " ".join(texts[i + 1 :]) or None))
        if pcm:
            pcm += gap
        rows.append(f"{len(pcm) / BYTES_PER_SECOND:.3f}\t{gesture}\t{to_display_text(text)}")
        pcm += voice
        print(f"  intro {i + 1}/{len(INTRO)}: {text}")
    (out / "intro.pcm").write_bytes(pcm)
    (out / "intro.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"intro: {len(pcm) / BYTES_PER_SECOND:.1f} s")


def make_answer(out: Path) -> None:
    pcm = tts.synthesize(ANSWER)
    (out / "answer.pcm").write_bytes(pcm)
    print(f"answer: {len(pcm) / BYTES_PER_SECOND:.1f} s")


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--force"]
    out = Path(args[0]) if args else Path(__file__).parent / "voice"
    out.mkdir(parents=True, exist_ok=True)
    s = get_settings()
    voice = [s.tts_provider, s.tts_model, s.elevenlabs_voice_id, tts.VOICE_SETTINGS, tts.SEED]
    want = {
        "intro": hashlib.sha256(json.dumps([INTRO, GAP_SECONDS, voice]).encode()).hexdigest()[:16],
        "answer": hashlib.sha256(json.dumps([ANSWER, voice]).encode()).hexdigest()[:16],
    }
    meta_path = out / "meta.json"
    try:
        have = {} if "--force" in sys.argv else json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        have = {}
    for name, make, files in (
        ("intro", make_intro, ["intro.pcm", "intro.tsv"]),
        ("answer", make_answer, ["answer.pcm"]),
    ):
        if have.get(name) == want[name] and all((out / f).exists() for f in files):
            print(f"{name}: sudah ada, dilewati")
            continue
        make(out)
        have[name] = want[name]
        meta_path.write_text(json.dumps(have, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
