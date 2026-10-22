// Pin dan konstanta perangkat. Pin dipilih yang aman di ESP32-S3 DevKitC (N8/N16R8):
// tidak memakai pin strapping, flash/PSRAM (26-37), atau USB (19-20).
#pragma once

// LCD ST7796 4" 320x480, SPI (FSPI).
#define PIN_TFT_SCLK 14
#define PIN_TFT_MOSI 18  // "SDI(MOSI)" di modul
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

// Tombol sendiri (bukan BOOT lagi): satu tombol antara GPIO7 dan GND, tanpa resistor
// (pin dipakai INPUT_PULLUP), jadi aktif LOW. Tahan = bicara, tekan 1x = putar ulang suara
// jawaban terakhir, tekan 2x = percakapan baru. Ditekan saat suara diputar = berhenti.
#define PIN_BUTTON 7
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
#define PIN_AMP_BCLK 16
#define PIN_AMP_LRC 17
#define PIN_AMP_DIN 15
#define SPEAKER_VOLUME 0.7f  // 0.0-1.0; di atas 1.0 suara pecah
// Audio ditampung dulu sebelum mulai diputar supaya tidak tersendat saat jaringan lambat.
#define SPEAKER_PREBUFFER_MS 300

// Perkenalan diunduh utuh ke PSRAM dulu, baru diputar: suaranya 32 KB/detik, jadi memutar
// sambil mengunduh membuat suara patah-patah begitu Wi-Fi melambat sesaat. Batas penampungnya
// 30 detik (960 KB di PSRAM, dilepas lagi setelah selesai); naskah sekarang ~14 detik.
#define INTRO_MAX_BYTES (30 * SAMPLE_RATE * 2)

// Perkenalan diri (suara + animasi) setiap kali menyala; 0 untuk langsung ke layar siap.
// Suaranya dibuat sekali dan disimpan server (GET /v1/intro), jadi tidak memakai kuota TTS.
#define INTRO_ON_BOOT 1

// Tertidur (layar redup) bila tidak ada pertanyaan selama ini; tekan tombol untuk membangunkan.
#define SLEEP_AFTER_MS (2 * 60 * 1000UL)
// Saat tidur: Wi-Fi hemat daya (tetap tersambung, pemberitahuan presensi tetap jalan) dan
// prosesor 80 MHz; dikembalikan penuh sebelum bangun/bertanya. 0 = matikan bila ada masalah.
#define SLEEP_POWER_SAVE 1
#define SLEEP_POWER_SAVE_AFTER_MS 5000  // setelah animasi masuk tidur selesai

// Kabar dari server (GET /v1/updates): kuliah berikutnya + pemberitahuan presensi/deadline.
#define UPDATES_EVERY_MS (2 * 60 * 1000UL)
// Lama pemberitahuan tampil bila tombol tidak ditekan.
#define ALERT_ATTENDANCE_MS 25000
#define ALERT_DEADLINE_MS 15000
#define ALERT_ATTENDED_MS 8000
#define ALERT_WARNING_MS 15000  // peringatan dini (kehadiran, anggaran)
#define ALERT_REVIEW_MS 12000   // waktunya mengulang topik dari kuis Tutor
// Presensi dibuka & deadline tugas dibacakan berulang: sekali saja sering terlewat didengar.
#define ALERT_SPEAK_TIMES 2
#define ALERT_SPEAK_GAP_MS 2500

// Mode Suara (diatur server, lihat voice.h): pesan status disimpan di PSRAM, masing-masing
// paling lama 10 detik; yang gagal diunduh dicoba lagi setelah VOICE_RETRY_MS.
#define VOICE_CLIP_MAX_BYTES (10 * SAMPLE_RATE * 2)
#define VOICE_RETRY_MS 60000
#define VOICE_THINKING_EVERY_MS 2000  // ketukan "sedang berpikir" selama menunggu jawaban
#define VOICE_IDLE_LOAD_MS 3000       // pesan status diunduh setelah menganggur selama ini

// Dikirim di header X-Firmware dan tampil di dashboard (Perangkat), jadi versi inilah cara
// memastikan build mana yang sedang terpasang: naikkan setiap kali kelakuan perangkat berubah.
// Server hanya memeriksa header ini ada atau tidak (kartu warning/review), bukan nilainya.
// 1.3: presensi & deadline membangunkan alat, berbunyi, dan dibacakan dua kali walau Mode Suara mati.
// 1.4: pin berubah - layar SCK/MOSI ke GPIO 14/18, tombol sendiri di GPIO 7 (bukan BOOT).
// 1.5: mode bahasa (Indonesia/Inggris, diatur server) dan pesan "ready" saat dibangunkan.
// 1.6: perkenalan diunduh utuh ke PSRAM dulu, tidak lagi diputar sambil mengunduh (suaranya
//      patah-patah bila Wi-Fi melambat sesaat).
#define FIRMWARE_VERSION "1.6"
