// Pratinjau layar EduPad di PC: menjalankan kode gambar yang sama dengan firmware (scene.cpp)
// tanpa LCD, dengan data tiruan, lalu menyimpan frame tiap layar sebagai RGB mentah
// (<nama>.rgb) untuk dijadikan GIF oleh make_gif.py.
#include <math.h>
#include <stdio.h>
#include <string.h>

#include <string>

#include <LovyanGFX.hpp>

#include "scene.h"

namespace {

constexpr int FPS = 30;
LGFX_Sprite canvas;
std::string outDir;

void push(const scene::Rect &) {}

// Rekam satu layar selama `seconds`; update(ui, t) mengisi data tiap frame.
template <typename F>
void record(const char *name, float seconds, scene::Ui ui, F update) {
  std::string path = outDir + "/" + name + ".rgb";
  FILE *out = fopen(path.c_str(), "wb");
  static uint8_t rgb[scene::W * scene::H * 3];
  int frames = 0;
  for (float t = 0; t < seconds; t += 1.0f / FPS, frames++) {
    ui.t = t;
    update(ui, t);
    scene::render(canvas, ui, frames == 0, push);
    canvas.readRectRGB(0, 0, scene::W, scene::H, rgb);
    fwrite(rgb, 1, sizeof rgb, out);
  }
  fclose(out);
  printf("%s: %d frame\n", name, frames);
}

void copy(char *dst, size_t size, const char *src) {
  strncpy(dst, src, size - 1);
  dst[size - 1] = 0;
}

}  // namespace

int main(int argc, char **argv) {
  outDir = argc > 1 ? argv[1] : ".";
  canvas.setColorDepth(16);
  if (!canvas.createSprite(scene::W, scene::H)) return 1;
  scene::begin();

  scene::Ui ui;
  ui.kind = scene::Kind::Boot;
  float shown = 0;
  record("boot", 5.8f, ui, [&](scene::Ui &u, float t) {
    struct Step {
      float at;
      const char *text;
      float progress;
    };
    static const Step steps[] = {{0.0f, "Menyalakan mikrofon", 0.15f},
                                 {1.2f, "Menyambung ke Kampus-WiFi", 0.45f},
                                 {3.0f, "Menghubungi server", 0.8f}};
    const Step *step = &steps[0];
    for (const Step &s : steps)
      if (t >= s.at) step = &s;
    bool done = t >= 4.6f;
    shown += ((done ? 1.0f : step->progress) - shown) * (1 - expf(-5.0f / FPS));
    copy(u.status, sizeof u.status, done ? "Siap!" : step->text);
    u.progress = shown;
    u.done = done ? t - 4.6f : -1;
  });

  ui = scene::Ui();
  ui.kind = scene::Kind::Home;
  record("home", 9.5f, ui, [](scene::Ui &, float) {});

  ui = scene::Ui();
  ui.kind = scene::Kind::Listen;
  float level = -90, lastLoud = 0;
  record("listen", 5.5f, ui, [&](scene::Ui &u, float t) {
    // bicara 0,3-2,4 s, lalu diam (memunculkan peringatan "suaramu pelan")
    float raw = (t > 0.3f && t < 2.4f) ? -30 + 9 * sinf(t * 7) * sinf(t * 2.3f) : -58 + 3 * sinf(t * 5);
    level += (raw - level) * (raw > level ? 0.6f : 0.15f);
    if (raw >= scene::SPEECH_DBFS) lastLoud = t;
    u.level = level;
    u.quiet = t - lastLoud;
    u.elapsedMs = (uint32_t)(t * 1000) + 250;
  });

  ui = scene::Ui();
  ui.kind = scene::Kind::Think;
  record("think", 4.0f, ui, [](scene::Ui &u, float t) { u.elapsedMs = (uint32_t)(t * 1000); });

  ui = scene::Ui();
  ui.kind = scene::Kind::Answer;
  copy(ui.title, sizeof ui.title, "PV Pertemuan 5: If-Else");
  copy(ui.subtitle, sizeof ui.subtitle, "materi pertemuan lima pemrograman visual apa");
  const char *lines[] = {"- Percabangan If-Else untuk memilih",
                         "  aksi sesuai kondisi",
                         "- ElseIf dan Nested If",
                         "- Operator logika: And, Or, Not",
                         "- Latihan: kalkulator nilai huruf",
                         "  dengan If-ElseIf"};
  ui.lineCount = 6;
  for (int i = 0; i < 6; i++) copy(ui.lines[i], sizeof ui.lines[i], lines[i]);
  record("answer", 5.0f, ui, [](scene::Ui &u, float t) {
    u.speaking = t < 3.5f;
    u.voice = u.speaking && sinf(t * 31) > -0.2f ? -22 : -60;
  });

  ui = scene::Ui();
  ui.kind = scene::Kind::Notice;
  ui.tone = scene::Tone::Warn;
  copy(ui.title, sizeof ui.title, "Suara tidak terdengar");
  copy(ui.lines[0], sizeof ui.lines[0], "Coba bicara lebih dekat, ya.");
  copy(ui.lines[1], sizeof ui.lines[1], "Tahan tombol lalu bicara lagi");
  ui.lineCount = 2;
  record("no_speech", 3.0f, ui, [](scene::Ui &, float) {});

  ui = scene::Ui();
  ui.kind = scene::Kind::Notice;
  ui.tone = scene::Tone::Error;
  copy(ui.title, sizeof ui.title, "Gagal terhubung");
  copy(ui.lines[0], sizeof ui.lines[0], "Server tidak menjawab (timeout)");
  copy(ui.lines[1], sizeof ui.lines[1], "Tahan tombol untuk mencoba lagi");
  ui.lineCount = 2;
  record("error", 3.0f, ui, [](scene::Ui &, float) {});

  // Perkenalan: kalimat dan waktu mulai seperti dari /v1/intro; "suara" tiruan naik-turun per suku kata.
  ui = scene::Ui();
  ui.kind = scene::Kind::Intro;
  struct Seg {
    float start;
    scene::Gesture gesture;
    const char *text;
  };
  static const Seg segs[] = {{0.0f, scene::Gesture::Wave, "Halo! Aku EduPad."},
                             {1.6f, scene::Gesture::Happy, "Teman belajarmu."},
                             {2.9f, scene::Gesture::Book, "Aku bisa menjelaskan materi kuliahmu,"},
                             {5.2f, scene::Gesture::Tasks, "mengecek tugas, deadline, dan presensi."},
                             {7.8f, scene::Gesture::Button, "Caranya gampang: tahan tombol, lalu tanya saja."},
                             {10.8f, scene::Gesture::Cheer, "Yuk, mulai belajar!"}};
  ui.segCount = 6;
  for (int i = 0; i < 6; i++) {
    ui.segStart[i] = segs[i].start;
    ui.segGesture[i] = segs[i].gesture;
    copy(ui.segText[i], sizeof ui.segText[i], segs[i].text);
  }
  ui.duration = 12.4f;
  record("intro", 13.4f, ui, [](scene::Ui &u, float t) {
    float pos = t - 0.5f;  // suara mulai setelah 0,5 s (unduh + prebuffer)
    u.position = pos;
    bool gap = false;
    for (int i = 1; i < 6; i++)
      if (pos > segs[i].start - 0.2f && pos < segs[i].start) gap = true;
    u.voice = (pos < 0 || pos > 12.4f || gap) ? -90 : (sinf(pos * 31) > -0.2f ? -22 : -45);
  });

  ui = scene::Ui();
  ui.kind = scene::Kind::Sleep;
  record("sleep", 8.0f, ui, [](scene::Ui &, float) {});

  ui = scene::Ui();
  ui.kind = scene::Kind::Home;
  record("wake", 4.0f, ui, [](scene::Ui &u, float t) { u.wake = t; });

  // Layar siap dengan kartu kuliah berikutnya (mulai 25 menit lagi: label berkedip)
  constexpr uint32_t NOW = 1792040400;  // 15 Okt 2026 09:00 WIB
  ui = scene::Ui();
  ui.kind = scene::Kind::Home;
  ui.hasNext = true;
  copy(ui.nextName, sizeof ui.nextName, "Prak EA");
  copy(ui.nextTime, sizeof ui.nextTime, "09:25");
  copy(ui.nextDay, sizeof ui.nextDay, "Hari ini");
  copy(ui.nextRoom, sizeof ui.nextRoom, "Laboratorium Komputer");
  ui.nextStart = NOW + 25 * 60;
  ui.nextEnd = ui.nextStart + 100 * 60;
  record("home_next", 3.0f, ui, [](scene::Ui &u, float t) { u.nowTs = NOW + (uint32_t)t; });

  ui = scene::Ui();
  ui.kind = scene::Kind::Alert;
  ui.alert = scene::Alert::Attendance;
  copy(ui.alertCourse, sizeof ui.alertCourse, "Statistika");
  copy(ui.alertDetail, sizeof ui.alertDetail, "Ruang 3.2 Gedung C");
  copy(ui.alertWhen, sizeof ui.alertWhen, "Tutup 09:20");
  ui.alertFrom = NOW - 10 * 60;
  ui.alertTo = NOW + 14 * 60 + 30;
  record("alert_presensi", 5.0f, ui, [](scene::Ui &u, float t) { u.nowTs = NOW + (uint32_t)t; });

  ui = scene::Ui();
  ui.kind = scene::Kind::Alert;
  ui.alert = scene::Alert::Attended;
  copy(ui.alertCourse, sizeof ui.alertCourse, "Prak SIG");
  copy(ui.alertDetail, sizeof ui.alertDetail, "Laboratorium Komputer");
  copy(ui.alertWhen, sizeof ui.alertWhen, "Pertemuan 6");
  record("alert_hadir", 3.0f, ui, [](scene::Ui &u, float t) { u.nowTs = NOW + (uint32_t)t; });

  ui = scene::Ui();
  ui.kind = scene::Kind::Alert;
  ui.alert = scene::Alert::Deadline;
  copy(ui.alertCourse, sizeof ui.alertCourse, "Prak PV");
  copy(ui.alertDetail, sizeof ui.alertDetail, "Laporan Praktikum 5: Percabangan If-Else dan Select Case");
  copy(ui.alertWhen, sizeof ui.alertWhen, "Besok 23:59");
  ui.alertTo = NOW + 39 * 3600 - 60;
  record("alert_deadline", 4.0f, ui, [](scene::Ui &u, float t) { u.nowTs = NOW + (uint32_t)t; });

  ui = scene::Ui();
  ui.kind = scene::Kind::Alert;
  ui.alert = scene::Alert::Warning;
  ui.alertHigh = true;
  copy(ui.alertCourse, sizeof ui.alertCourse, "Prak PV");
  copy(ui.alertDetail, sizeof ui.alertDetail, "Batas kehadiran terlewati");
  copy(ui.alertWhen, sizeof ui.alertWhen, "Peringatan");
  record("alert_peringatan", 3.0f, ui, [](scene::Ui &u, float t) { u.nowTs = NOW + (uint32_t)t; });

  ui = scene::Ui();
  ui.kind = scene::Kind::Alert;
  ui.alert = scene::Alert::Review;
  copy(ui.alertCourse, sizeof ui.alertCourse, "MSBD P2");
  copy(ui.alertDetail, sizeof ui.alertDetail, "Database Engine dan Struktur Indeks");
  copy(ui.alertWhen, sizeof ui.alertWhen, "Penguasaan 40%");
  record("alert_ulang", 3.0f, ui, [](scene::Ui &u, float t) { u.nowTs = NOW + (uint32_t)t; });

  ui = scene::Ui();
  ui.kind = scene::Kind::Portal;
  copy(ui.ssid, sizeof ui.ssid, "EduPad-Setup");
  copy(ui.password, sizeof ui.password, "edupad123");
  copy(ui.ip, sizeof ui.ip, "192.168.4.1");
  copy(ui.subtitle, sizeof ui.subtitle, "Kampus-WiFi");
  record("portal", 2.0f, ui, [](scene::Ui &, float) {});
  return 0;
}
