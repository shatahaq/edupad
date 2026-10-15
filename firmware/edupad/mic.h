// Mikrofon INMP441 lewat I2S. Task latar membaca terus; selama start()..stop() sampel
// PCM 16-bit mono 16 kHz (format /v1/ask) ditampung untuk dibaca dengan read().
#pragma once

#include <Arduino.h>

namespace mic {

bool begin();
void start();
void stop();
// Ambil PCM yang tertampung, menunggu paling lama `waitMs` bila kosong.
size_t read(uint8_t *dst, size_t maxBytes, uint32_t waitMs);
size_t available();
// Level suara terakhir (RMS, dBFS, turun perlahan), untuk meter di layar.
float levelDbfs();
// Byte yang dibuang karena penampung penuh (koneksi terlalu lambat).
uint32_t droppedBytes();

}  // namespace mic
