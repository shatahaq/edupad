// IMA ADPCM 4-bit dari server (?format=adpcm, src/edupad/voice/adpcm.py): seperempat ukuran PCM,
// jadi suara terunduh empat kali lebih cepat. Blok = header 4 byte (predictor int16 little-endian,
// index, 1 byte kosong) + nibble, nibble rendah dulu; 256 sampel per blok, blok terakhir boleh
// lebih pendek. Tabel dan urutan bit harus tetap sama dengan encoder di server.
#pragma once

#include <Arduino.h>

namespace adpcm {

constexpr size_t BLOCK_SAMPLES = 256;
constexpr size_t BLOCK_BYTES = 4 + BLOCK_SAMPLES / 2;

// Satu blok (paling banyak BLOCK_BYTES byte) -> sampel PCM di `out` (muat BLOCK_SAMPLES).
// Mengembalikan jumlah sampel; 0 bila blok terlalu pendek.
size_t decodeBlock(const uint8_t *block, size_t size, int16_t *out);

}  // namespace adpcm
