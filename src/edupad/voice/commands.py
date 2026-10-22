"""Perintah setelan yang dijawab server sendiri, tanpa memanggil LLM maupun TTS.

"Aktifkan mode suara", "matikan mode suara", "bicara lebih cepat/lambat", dan "ganti ke bahasa
Inggris" selalu berakhir pada salah satu dari beberapa kalimat yang sama. Menyusunnya lewat agent
berarti membayar dua panggilan LLM (satu memilih tool, satu menyusun `answer`) dan satu panggilan
TTS untuk kalimat yang sudah diketahui sejak awal. Di sini transkrip STT dicocokkan ke pola di
bawah: yang cocok langsung mengubah setelan lalu dijawab kalimat template, suaranya dibaca dari
simpanan disk (voice/clips.py). Yang tidak cocok diteruskan ke agent seperti biasa.

Polanya sengaja fullmatch dan daftar katanya pendek: "aktifkan mode suara" dilayani di sini,
tetapi "apa itu mode suara?" tetap dijawab agent. Lebih baik satu perintah lolos ke LLM
daripada satu pertanyaan dibalas template yang salah.

Pola bahasa Indonesia dan Inggris dicocokkan bersama-sama, apa pun bahasa yang sedang aktif:
"switch to English" harus tetap dikenali saat EduPad masih berbahasa Indonesia, dan "ganti ke
bahasa Indonesia" saat sudah berbahasa Inggris.

Kecepatan diubah relatif (satu tingkat dari setelan sekarang), jadi "lebih cepat" berturut-turut
menaik sampai batas, bukan melompat ke nilai yang ditebak model.
"""

from __future__ import annotations

import logging
import re

from edupad.agent.formatting import fit_screen
from edupad.voice import clips, lang
from edupad.voice import mode as voice_mode

log = logging.getLogger(__name__)

URL_PREFIX = "/v1/voice/reply/"

# Kata sopan/sapaan yang boleh mengapit perintah tanpa mengubah maksudnya.
_FILLER = r"(?:tolong|coba|edupad|eduped|ya|dong|deh|sekarang|please|ok|okay|hey|now)"
_PAD, _TAIL = rf"(?:{_FILLER}\s+)*", rf"(?:\s+{_FILLER})*"
_MODE = r"mode\s+(?:suara|tunanetra|bicara)"
_TALK = r"(?:bicara|berbicara|ngomong|baca|bacanya|suaranya|bicaranya)"
_SPEAK = r"(?:speak|talk|read)(?:ing)?"
_VOICE_MODE = r"voice\s+mode"
_SWITCH = r"(?:ganti|ubah|pindah|pakai|pake|gunakan)\s+(?:ke\s+)?(?:bahasa\s+)?"

# (nama, pola) -> dicoba berurutan; yang pertama cocok dipakai.
PATTERNS = [
    (
        "english",
        rf"{_SWITCH}(?:inggris|english)|(?:switch|change)\s+to\s+english|{_SPEAK}\s+(?:in\s+)?"
        r"english|(?:use|in)\s+english|english\s+(?:mode|please)|mode\s+(?:bahasa\s+)?inggris",
    ),
    (
        "indonesian",
        rf"{_SWITCH}indonesia|(?:switch|change)\s+to\s+(?:bahasa\s+)?indonesian?|{_SPEAK}\s+"
        r"(?:in\s+)?(?:bahasa\s+)?indonesian?|bahasa\s+indonesia",
    ),
    (
        "on",
        rf"(?:aktifkan|aktifin|nyalakan|nyalain|hidupkan|mulai)\s+{_MODE}"
        rf"|(?:turn\s+on|enable|start)\s+{_VOICE_MODE}",
    ),
    (
        "off",
        rf"(?:matikan|matiin|nonaktifkan|hentikan|keluar\s+dari)\s+{_MODE}"
        rf"|(?:turn\s+off|disable|stop|exit|quit)\s+{_VOICE_MODE}",
    ),
    (
        "faster",
        rf"(?:{_TALK}\s+)?lebih\s+cepat|percepat(?:\s+{_TALK})?"
        rf"|{_SPEAK}\s+faster|speed\s+up",
    ),
    (
        "slower",
        rf"(?:{_TALK}\s+)?lebih\s+(?:lambat|pelan)|perlambat(?:\s+{_TALK})?"
        rf"|{_SPEAK}\s+slower|slow\s+down",
    ),
]
_COMPILED = [(name, re.compile(rf"{_PAD}(?:{body}){_TAIL}")) for name, body in PATTERNS]

# Kalimat tetap per hasil, dua bahasa (voice/lang.py). `lines` sudah dipotong lagi oleh
# fit_screen agar pas di LCD. Konfirmasi ganti bahasa selalu memakai bahasa yang baru, jadi
# "english"/"indonesian" isinya sama di kedua kunci.
REPLIES = {
    "on": {
        "id": {
            "speech": "Mode suara aktif. Semua jawaban dan pemberitahuan sekarang dibacakan "
            "lengkap. Untuk mematikannya, ucapkan matikan mode suara.",
            "title": "Mode Suara aktif",
            "lines": ["Jawaban & pemberitahuan dibacakan penuh", "Matikan: 'matikan mode suara'"],
        },
        "en": {
            "speech": "Voice mode is on. Every answer and alert is now read out in full. "
            "To turn it off, say turn off voice mode.",
            "title": "Voice mode on",
            "lines": ["Answers & alerts read out in full", "Turn off: 'turn off voice mode'"],
        },
    },
    "off": {
        "id": {
            "speech": "Mode suara dimatikan. Jawaban tetap dibacakan singkat, rinciannya di layar.",
            "title": "Mode Suara mati",
            "lines": ["Jawaban dibacakan singkat", "Rinciannya tampil di layar"],
        },
        "en": {
            "speech": "Voice mode is off. Answers are still read out, but briefly; "
            "the details stay on the screen.",
            "title": "Voice mode off",
            "lines": ["Answers read out briefly", "Details stay on the screen"],
        },
    },
    "lambat": {
        "id": {
            "speech": "Baik, aku bicara lebih lambat.",
            "title": "Kecepatan: lambat",
            "lines": ["Ucapkan 'bicara lebih cepat' untuk menaikkan"],
        },
        "en": {
            "speech": "Alright, I will speak more slowly.",
            "title": "Speed: slow",
            "lines": ["Say 'speak faster' to speed up"],
        },
    },
    "normal": {
        "id": {
            "speech": "Baik, kecepatan bicaraku kembali normal.",
            "title": "Kecepatan: normal",
            "lines": ["Bisa diubah: 'bicara lebih cepat' / 'lebih lambat'"],
        },
        "en": {
            "speech": "Alright, back to my normal speaking speed.",
            "title": "Speed: normal",
            "lines": ["Change it: 'speak faster' / 'speak slower'"],
        },
    },
    "cepat": {
        "id": {
            "speech": "Baik, aku bicara lebih cepat.",
            "title": "Kecepatan: cepat",
            "lines": ["Ucapkan 'bicara lebih lambat' untuk menurunkan"],
        },
        "en": {
            "speech": "Alright, I will speak faster.",
            "title": "Speed: fast",
            "lines": ["Say 'speak slower' to slow down"],
        },
    },
    "sangat_cepat": {
        "id": {
            "speech": "Baik, ini kecepatan bicaraku yang paling cepat.",
            "title": "Kecepatan: sangat cepat",
            "lines": ["Ucapkan 'bicara lebih lambat' untuk menurunkan"],
        },
        "en": {
            "speech": "Alright, this is my fastest speaking speed.",
            "title": "Speed: very fast",
            "lines": ["Say 'speak slower' to slow down"],
        },
    },
    "fastest": {
        "id": {
            "speech": "Ini sudah kecepatan paling cepat.",
            "title": "Sudah paling cepat",
            "lines": ["Ucapkan 'bicara lebih lambat' untuk menurunkan"],
        },
        "en": {
            "speech": "This is already the fastest speed.",
            "title": "Already the fastest",
            "lines": ["Say 'speak slower' to slow down"],
        },
    },
    "slowest": {
        "id": {
            "speech": "Ini sudah kecepatan paling lambat.",
            "title": "Sudah paling lambat",
            "lines": ["Ucapkan 'bicara lebih cepat' untuk menaikkan"],
        },
        "en": {
            "speech": "This is already the slowest speed.",
            "title": "Already the slowest",
            "lines": ["Say 'speak faster' to speed up"],
        },
    },
    "english": dict.fromkeys(
        lang.LANGUAGES,
        {
            "speech": "English mode is on. From now on I answer in English, and everything on "
            "the screen is in English too. To switch back, say ganti ke bahasa Indonesia.",
            "title": "English mode on",
            "lines": ["Answers, alerts & screen in English", "Back: 'ganti ke bahasa Indonesia'"],
        },
    ),
    "indonesian": dict.fromkeys(
        lang.LANGUAGES,
        {
            "speech": "Bahasa Indonesia aktif kembali. Mulai sekarang aku menjawab dalam bahasa "
            "Indonesia. Untuk kembali ke bahasa Inggris, ucapkan switch to English.",
            "title": "Bahasa Indonesia",
            "lines": ["Jawaban & layar bahasa Indonesia", "Ke Inggris: 'switch to English'"],
        },
    ),
}

SPEED_ORDER = list(voice_mode.SPEEDS)  # lambat -> sangat_cepat
LANGUAGE_REPLIES = {"english": "en", "indonesian": "id"}


def _normalize(text: str) -> str:
    """Huruf kecil tanpa tanda baca, spasi dirapatkan: transkrip STT tidak selalu rapi."""
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]+", " ", text.lower())).strip()


def _match(text: str) -> str | None:
    spoken = _normalize(text)
    return next((name for name, pattern in _COMPILED if pattern.fullmatch(spoken)), None)


def _step(up: bool) -> str:
    """Naik/turun satu tingkat kecepatan; nama balasan bila sudah di ujung."""
    at = SPEED_ORDER.index(voice_mode.load()["speed"])
    to = at + (1 if up else -1)
    if not 0 <= to < len(SPEED_ORDER):
        return "fastest" if up else "slowest"
    voice_mode.save(speed=SPEED_ORDER[to])
    return SPEED_ORDER[to]


def reply(name: str) -> dict:
    """Kalimat template `name` dalam bahasa yang aktif."""
    return lang.pick(REPLIES[name])


def handle(text: str) -> dict | None:
    """Terapkan perintah setelan dalam `text` dan kembalikan jawaban siap kirim; None bila
    ucapan ini bukan perintah setelan dan harus diteruskan ke agent."""
    command = _match(text)
    if command is None:
        return None
    if command in LANGUAGE_REPLIES:
        lang.save(LANGUAGE_REPLIES[command])  # balasannya memakai bahasa yang baru
        reply_name = command
    elif command in ("on", "off"):
        voice_mode.save(enabled=command == "on")
        reply_name = command
    else:
        reply_name = _step(up=command == "faster")
    chosen = reply(reply_name)
    log.info("[setelan suara] perintah %r dijawab template %s (tanpa LLM)", text, reply_name)
    return {
        "speech": chosen["speech"],
        "screen": fit_screen(chosen["title"], chosen["lines"]),
        "detail": "",
        "reply": reply_name,
        "audio_url": f"{URL_PREFIX}{reply_name}?v={_audio_version(reply_name)}",
    }


def _audio_version(name: str) -> str:
    return clips.version(reply(name)["speech"], voice_mode.speed_value())


def load(name: str) -> bytes:
    """PCM kalimat template `name`; KeyError bila tidak dikenal, tts.TTSError bila TTS gagal."""
    return clips.cached_pcm(
        f"reply-{name}",
        reply(name)["speech"],
        voice_mode.speed_value(),
        [v["speech"] for v in REPLIES[name].values()],
    )
