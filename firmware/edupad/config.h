// Pin dan konstanta perangkat. Pin dipilih yang aman di ESP32-S3 DevKitC (N8/N16R8):
// tidak memakai pin strapping, flash/PSRAM (26-37), atau USB (19-20).
#pragma once

// LCD ST7796 4" 320x480, SPI (FSPI).
#define PIN_TFT_SCLK 12
#define PIN_TFT_MOSI 11  // "SDI(MOSI)" di modul
#define PIN_TFT_MISO -1  // "SDO(MISO)" tidak dipakai, biarkan lepas
#define PIN_TFT_CS 10
#define PIN_TFT_DC 9  // "DC/RS"
#define PIN_TFT_RST 13
#define PIN_TFT_BL 21  // "LED"; -1 bila disambung langsung ke 3V3
#define TFT_SPI_HZ 40000000
// Bila warna terbalik (latar putih / merah jadi biru), ubah salah satu ini.
#define TFT_INVERT false
#define TFT_BGR false

// Mikrofon INMP441, I2S. L/R ke GND = kanal kiri.
#define PIN_MIC_SCK 4  // BCLK
#define PIN_MIC_WS 5   // LRCLK
#define PIN_MIC_SD 6   // data
#define MIC_USE_RIGHT_CHANNEL 0  // ubah ke 1 bila L/R ke 3V3 (atau meter tetap 0)
// INMP441 pelan: sampel 24-bit digeser ke 16-bit dengan penguatan 2^(16-SHIFT).
// 12 = +24 dB. Server menganggap hening bila lebih pelan dari -35 dBFS (lihat stt.SPEECH_DBFS):
// saat bicara normal, meter di layar sebaiknya sering melewati garis kuning.
#define MIC_GAIN_SHIFT 12

// Tombol: BOOT (GPIO0) di papan, aktif LOW. Tahan = bicara, tekan 1x = putar ulang suara
// jawaban terakhir, tekan 2x = percakapan baru. Ditekan saat suara diputar = berhenti.
#define PIN_BUTTON 0
#define SHORT_PRESS_MS 400  // dilepas lebih cepat dari ini = tekan singkat
#define DOUBLE_TAP_MS 350   // jeda maksimum antara dua tekan singkat
#define MAX_RECORD_MS 60000

#define SAMPLE_RATE 16000
// Penampung rekaman selama koneksi TLS dibuka (~0,5-2 s): 3 s = 96 KB.
#define AUDIO_BUFFER_BYTES (3 * SAMPLE_RATE * 2)
#define RESPONSE_TIMEOUT_MS 60000

// Hotspot pengaturan Wi-Fi bila Wi-Fi tersimpan dan bawaan tidak tersambung.
#define SETUP_AP_SSID "EduPad-Setup"
#define SETUP_AP_PASSWORD "edupad123"  // minimal 8 karakter
#define WIFI_CONNECT_TIMEOUT_MS 12000  // per jaringan yang dicoba

// Amplifier I2S MAX98357A (sama dengan speaker_test). GAIN dan SD tidak disambung.
#define PIN_AMP_BCLK 15
#define PIN_AMP_LRC 16
#define PIN_AMP_DIN 17
#define SPEAKER_VOLUME 0.7f  // 0.0-1.0; di atas 1.0 suara pecah
// Audio ditampung dulu sebelum mulai diputar supaya tidak tersendat saat jaringan lambat.
#define SPEAKER_PREBUFFER_MS 300
