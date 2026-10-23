"""IMA ADPCM 4-bit untuk suara ke perangkat: seperempat ukuran PCM 16-bit.

PCM 16 kHz = 32 KB per detik suara, sedangkan ESP32 mengunduh lewat TLS hanya ±53 KB/detik
(terukur dari perangkat, 2026-10-23). Firmware memutar suara setelah unduhan utuh, jadi ukuran
langsung menjadi jeda sebelum EduPad bicara. Dengan ADPCM (8,25 KB/detik) jeda itu tinggal
seperempat. Dekodernya di firmware/edupad/adpcm.cpp, tabel dan urutan bit harus tetap sama.

Format: blok-blok 256 sampel. Tiap blok = header 4 byte (predictor int16 little-endian, index
uint8, 1 byte kosong) + 128 byte nibble, nibble rendah dulu. Header memuat keadaan encoder,
jadi tiap blok bisa didekode sendiri. Blok terakhir boleh lebih pendek; jumlah sampel ganjil
diisi satu nibble nol (satu sampel tambahan yang tak terdengar).
"""

from __future__ import annotations

import struct

BLOCK_SAMPLES = 256
HEADER_BYTES = 4
BLOCK_BYTES = HEADER_BYTES + BLOCK_SAMPLES // 2
FORMAT = f"adpcm_ima;rate=16000;channels=1;block={BLOCK_SAMPLES}"

STEP = [
    7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45, 50, 55, 60, 66,
    73, 80, 88, 97, 107, 118, 130, 143, 157, 173, 190, 209, 230, 253, 279, 307, 337, 371, 408,
    449, 494, 544, 598, 658, 724, 796, 876, 963, 1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066,
    2272, 2499, 2749, 3024, 3327, 3660, 4026, 4428, 4871, 5358, 5894, 6484, 7132, 7845, 8630,
    9493, 10442, 11487, 12635, 13899, 15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794,
    32767,
]  # fmt: skip
INDEX = [-1, -1, -1, -1, 2, 4, 6, 8, -1, -1, -1, -1, 2, 4, 6, 8]

# Selisih bertanda dan index berikutnya untuk tiap (index, kode), dihitung sekali: encoder
# berjalan per sampel di Python, jadi cabang di dalam loop dibuat seminimal mungkin.
_DIFF = [[0] * 16 for _ in STEP]
_NEXT = [[0] * 16 for _ in STEP]
for _i, _step in enumerate(STEP):
    for _code in range(16):
        _d = _step >> 3
        if _code & 4:
            _d += _step
        if _code & 2:
            _d += _step >> 1
        if _code & 1:
            _d += _step >> 2
        _DIFF[_i][_code] = -_d if _code & 8 else _d
        _NEXT[_i][_code] = min(88, max(0, _i + INDEX[_code]))


class Encoder:
    """Encoder bertahap: PCM masuk sepotong-sepotong (mis. dari TTS), blok utuh keluar."""

    def __init__(self):
        self._predictor, self._index = 0, 0
        self._pending = b""

    def feed(self, pcm: bytes) -> bytes:
        """Blok-blok utuh dari PCM yang sudah masuk; sisanya ditahan sampai feed/flush berikutnya."""
        data = self._pending + pcm
        whole = len(data) - len(data) % (BLOCK_SAMPLES * 2)
        self._pending = data[whole:]
        return self._encode(data[:whole])

    def flush(self) -> bytes:
        """Blok terakhir (lebih pendek) dari sisa PCM."""
        data, self._pending = self._pending, b""
        return self._encode(data[: len(data) - len(data) % 2])

    def _encode(self, pcm: bytes) -> bytes:
        samples = struct.unpack(f"<{len(pcm) // 2}h", pcm)
        out = bytearray()
        predictor, index = self._predictor, self._index
        for start in range(0, len(samples), BLOCK_SAMPLES):
            out += struct.pack("<hBB", predictor, index, 0)
            low = -1
            for sample in samples[start : start + BLOCK_SAMPLES]:
                step = STEP[index]
                diff = sample - predictor
                code = 0
                if diff < 0:
                    code, diff = 8, -diff
                if diff >= step:
                    code |= 4
                    diff -= step
                if diff >= step >> 1:
                    code |= 2
                    diff -= step >> 1
                if diff >= step >> 2:
                    code |= 1
                predictor += _DIFF[index][code]
                if predictor > 32767:
                    predictor = 32767
                elif predictor < -32768:
                    predictor = -32768
                index = _NEXT[index][code]
                if low < 0:
                    low = code
                else:
                    out.append(low | code << 4)
                    low = -1
            if low >= 0:
                out.append(low)
        self._predictor, self._index = predictor, index
        return bytes(out)


def encode(pcm: bytes) -> bytes:
    encoder = Encoder()
    return encoder.feed(pcm) + encoder.flush()


def decode(data: bytes) -> bytes:
    """Kebalikan encode (untuk tes dan ?format=wav dari ADPCM); sama dengan dekoder firmware."""
    samples: list[int] = []
    for start in range(0, len(data), BLOCK_BYTES):
        block = data[start : start + BLOCK_BYTES]
        if len(block) < HEADER_BYTES:
            break
        predictor, index, _ = struct.unpack("<hBB", block[:HEADER_BYTES])
        index = min(index, 88)
        for byte in block[HEADER_BYTES:]:
            for code in (byte & 0x0F, byte >> 4):
                predictor = max(-32768, min(32767, predictor + _DIFF[index][code]))
                index = _NEXT[index][code]
                samples.append(predictor)
    return struct.pack(f"<{len(samples)}h", *samples)
