// Speaker lewat amplifier I2S MAX98357A. Masukan: PCM 16-bit mono 16 kHz (format /v1/audio).
#pragma once

#include <Arduino.h>

namespace speaker {

bool begin();
// Boleh dipanggil dengan jumlah byte ganjil: sisa 1 byte disimpan untuk panggilan berikutnya.
// Menunggu bila buffer DMA penuh (seiring kecepatan putar).
void write(const uint8_t *pcm, size_t size);
// Akhir audio: putar sisa yang masih ditampung.
void finish();
// Hentikan suara seketika dan buang sisa.
void stop();
// Bunyi "ding-dong" singkat (~0,9 s) untuk pemberitahuan; dibuat di perangkat, tanpa server.
void chime();
// Keras suara (dBFS) yang sedang keluar, untuk gerak paruh burung hantu.
float level();
// Lama audio yang sudah terdengar sejak write() pertama (ms), untuk menyelaraskan layar.
uint32_t positionMs();

}  // namespace speaker
