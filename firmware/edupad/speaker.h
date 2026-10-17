// Speaker lewat amplifier I2S MAX98357A. Masukan: PCM 16-bit mono 16 kHz (format /v1/audio).
// Dua sumber: suara dari server (write/finish/stop, dari loop) dan efek suara earcon.h yang
// diputar task latar (effects). Suara server selalu didahulukan: efek berhenti begitu write()
// dipanggil dan tidak diputar sampai finish()/stop().
#pragma once

#include <Arduino.h>

#include "earcon.h"

namespace speaker {

bool begin();
// Boleh dipanggil dengan jumlah byte ganjil: sisa 1 byte disimpan untuk panggilan berikutnya.
// Menunggu bila buffer DMA penuh (seiring kecepatan putar).
void write(const uint8_t *pcm, size_t size);
// Akhir audio: putar sisa yang masih ditampung.
void finish();
// Hentikan suara seketika dan buang sisa.
void stop();
// Jadwalkan efek suara: cues[i].sound pada baseMs (millis) + cues[i].at detik. Menggantikan efek
// yang sedang/akan diputar. Efek yang terlambat > 250 ms dilewati. Bila SOUND_EFFECTS 0 hanya
// bunyi presensi dibuka yang tetap diputar. Aman dipanggil dari task mana pun, juga sebelum begin().
void effects(const earcon::Cue *cues, int count, uint32_t baseMs);
// Keras suara (dBFS) yang sedang keluar, untuk gerak paruh burung hantu.
float level();
// Lama audio yang sudah terdengar sejak write() pertama (ms), untuk menyelaraskan layar.
uint32_t positionMs();

}  // namespace speaker
