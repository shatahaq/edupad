// Gambar layar EduPad yang tidak bergantung pada perangkat keras. Dipakai firmware (display.cpp)
// dan pratinjau di PC (../preview). Semua fungsi menggambar ke kanvas (sprite) dan hanya
// mengubah piksel di dalam area clip yang aktif, jadi bisa dipakai untuk menggambar ulang
// sebagian layar.
#pragma once

#include <LovyanGFX.hpp>

namespace scene {

constexpr int W = 480;
constexpr int H = 320;

struct Rect {
  int x, y, w, h;
};

enum class Kind : uint8_t {
  Boot,    // menyala: burung hantu jatuh, bangun, melambai + status dan progress
  Home,    // siap: petunjuk cara bertanya
  Listen,  // tombol ditahan: batang suara mengikuti level mikrofon
  Think,   // menunggu jawaban server
  Answer,  // judul + butir jawaban; burung hantu bicara selama suara diputar
  Notice,  // pesan singkat (info / peringatan / galat)
  Portal,  // petunjuk pengaturan Wi-Fi lewat hotspot
  Intro,   // perkenalan diri setelah menyala: kalimat diketik mengikuti suara + gerakan
  Sleep,   // tidak ada pertanyaan beberapa menit: menguap, berselimut, Zzz; layar meredup
  Alert,   // pemberitahuan dari server: presensi dibuka / tercatat, deadline dekat
};

// Warning = peringatan dini (kehadiran/anggaran), Review = waktunya mengulang topik (Tutor).
enum class Alert : uint8_t { Attendance, Attended, Deadline, Warning, Review };

enum class Tone : uint8_t { Info, Warn, Error };

// Gerakan burung hantu per kalimat perkenalan (nama dari server: voice/intro.py).
enum class Gesture : uint8_t { Talk, Wave, Happy, Book, Tasks, Button, Cheer };

constexpr int MAX_LINES = 9;
constexpr int MAX_SEGMENTS = 8;

// Semua yang ditampilkan. Diisi display.cpp (atau pratinjau), dibaca saat menggambar.
struct Ui {
  Kind kind = Kind::Boot;
  float t = 0;  // detik sejak layar ini mulai
  uint32_t nowTs = 0;  // detik epoch sekarang (jam dari server); 0 = belum tahu

  // Boot
  char status[48] = "";
  float progress = 0;  // 0..1, sudah dihaluskan
  float done = -1;     // detik sejak siap; negatif = belum

  // Home
  bool newSession = false;
  bool online = true;
  // Home / Listen: detik sejak dibangunkan dari tidur (animasi bangun); negatif = tidak
  float wake = -1;
  // Home: kuliah berikutnya (dari /v1/updates)
  bool hasNext = false;
  char nextName[24] = "";  // nama singkat, mis. "Prak MSBD"
  char nextTime[8] = "";   // "08:00"
  char nextDay[12] = "";   // "Hari ini" / "Besok" / "Kamis"
  char nextRoom[40] = "";
  uint32_t nextStart = 0, nextEnd = 0;
  char warning[56] = "";  // mis. sesi SATU habis; tampil di baris petunjuk layar siap

  // Alert
  Alert alert = Alert::Attendance;
  char alertCourse[32] = "";
  char alertDetail[64] = "";  // ruang (presensi) atau judul tugas (deadline)
  char alertWhen[32] = "";    // "Tutup 10:40" / "Besok 23:59" / "Pertemuan 5"
  bool alertQr = true;        // presensi: lewat QR di kelas (false = isi di portal SATU)
  bool alertHigh = false;     // peringatan prioritas tinggi (mis. batas kehadiran terlewati)
  uint32_t alertFrom = 0, alertTo = 0;  // jendela presensi / deadline (detik epoch)

  // Listen / Think
  uint32_t elapsedMs = 0;
  float level = -90;  // dBFS, sudah dihaluskan
  float quiet = 0;    // detik sejak terakhir terdengar suara cukup keras

  // Answer / Notice / Portal
  Tone tone = Tone::Info;
  char title[48] = "";
  char subtitle[96] = "";  // Answer: pertanyaan; Portal: jaringan yang gagal
  // Answer: baris dari server ("- " = butir baru, "  " = lanjutan). Notice: baris pesan.
  char lines[MAX_LINES][48] = {};
  uint8_t lineCount = 0;
  bool speaking = false;

  // Intro: kalimat yang tampil ditentukan posisi suara
  uint8_t segCount = 0;
  float segStart[MAX_SEGMENTS] = {};
  Gesture segGesture[MAX_SEGMENTS] = {};
  char segText[MAX_SEGMENTS][64] = {};
  float position = -1;  // detik suara perkenalan yang sudah terdengar; negatif = belum mulai
  float duration = 0;

  // Answer / Intro: keras suara yang sedang diputar (dBFS, dihaluskan) untuk gerak paruh
  float voice = -90;

  // Portal
  char ssid[33] = "";
  char password[33] = "";
  char ip[16] = "";

  // Notifikasi kecil di bawah layar
  char toast[48] = "";
  float toastT = -1;  // detik sejak muncul; negatif = tidak ada
};

// Ambang "ada suara" server (stt.SPEECH_DBFS), dipakai warna batang suara.
constexpr float SPEECH_DBFS = -35.0f;
// Paruh terbuka bila suara yang diputar lebih keras dari ini.
constexpr float MOUTH_DBFS = -30.0f;
// Lama notifikasi kecil tampil (detik).
constexpr float TOAST_SECONDS = 2.5f;
// Layar tidur: lama animasi tertidur sebelum layar diredupkan (detik).
constexpr float SLEEP_SETTLE_SECONDS = 3.0f;
// Layar tidur: setelah menguap (berdiri), pindah ke kamar tidur pada detik ini.
constexpr float SLEEP_ROOM_AT = 2.2f;
// Bangun dari kamar: detik pertama masih di kamar (kaget di ranjang) sebelum ke layar siap.
constexpr float WAKE_ROOM_SECONDS = 0.7f;

// Memuat font dan menyiapkan latar. psram: simpan salinan latar (300 KB) di PSRAM (ESP32).
void begin(bool psram = false);
// Latar gradasi biru malam di area clip.
void background(lgfx::LovyanGFX &g);
// Satu frame ke kanvas penuh (W x H). full = gambar seluruh layar (saat layar berganti); selain
// itu hanya bagian yang bergerak. push(area) dipanggil untuk tiap area yang berubah supaya hanya
// bagian itu yang dikirim ke LCD.
void render(lgfx::LovyanGFX &canvas, const Ui &ui, bool full, void (*push)(const Rect &area));

}  // namespace scene
