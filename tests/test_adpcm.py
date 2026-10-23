import math
import struct

from edupad.voice import adpcm

# Satu detik suara buatan yang naik-turun seperti ucapan (bukan senyap atau nada tunggal).
PCM = b"".join(
    struct.pack("<h", int(12000 * math.sin(i / 5) * math.sin(i / 1500))) for i in range(16000)
)


def snr_db(a: bytes, b: bytes) -> float:
    n = len(a) // 2
    x, y = struct.unpack(f"<{n}h", a), struct.unpack(f"<{n}h", b[: n * 2])
    noise = sum((p - q) ** 2 for p, q in zip(x, y, strict=True))
    return 10 * math.log10(sum(p * p for p in x) / noise)


def test_round_trip_is_a_quarter_the_size_and_sounds_close():
    data = adpcm.encode(PCM)
    blocks = math.ceil(len(PCM) / 2 / adpcm.BLOCK_SAMPLES)
    assert len(data) == len(PCM) // 4 + blocks * adpcm.HEADER_BYTES
    back = adpcm.decode(data)
    assert len(back) == len(PCM)  # 16000 sampel = 62 blok penuh + 128 sampel, genap
    assert snr_db(PCM, back) > 20


def test_streaming_encoder_matches_whole_encode():
    encoder, out = adpcm.Encoder(), b""
    for start in range(0, len(PCM), 777):  # potongan TTS tak sejajar blok maupun sampel
        out += encoder.feed(PCM[start : start + 777])
    assert out + encoder.flush() == adpcm.encode(PCM)


def test_every_block_decodes_on_its_own():
    data = adpcm.encode(PCM)
    second = data[adpcm.BLOCK_BYTES : 2 * adpcm.BLOCK_BYTES]
    alone = adpcm.decode(second)  # header blok membawa keadaan encoder
    whole = adpcm.decode(data)
    start = adpcm.BLOCK_SAMPLES * 2
    assert alone == whole[start : start + len(alone)]


def test_short_and_odd_input():
    assert adpcm.encode(b"") == b""
    three = struct.pack("<3h", 1000, -1000, 500)
    data = adpcm.encode(three)
    assert len(data) == adpcm.HEADER_BYTES + 2  # 3 sampel + satu nibble pengisi
    assert len(adpcm.decode(data)) == 4 * 2
