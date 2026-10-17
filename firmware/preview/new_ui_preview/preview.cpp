// Salinan ../preview.cpp untuk eksperimen gaya Duolingo (scene.cpp di folder ini): data tiruan
// sama, beberapa layar direkam lebih lama supaya gerakannya terlihat utuh, ditambah layar siap
// saat Wi-Fi terputus.
//
// preview OUT              -> OUT/<layar>.rgb (frame RGB 480x320, 30 fps) untuk make_gif.py
// preview OUT VOICE_DIR    -> juga OUT/<layar>.pcm (16 kHz mono): efek suara earcon.h + suara
//                             TTS asli dari VOICE_DIR (make_voice.py), untuk make_video.py.
//                             Perkenalan dan jawaban lalu mengikuti waktu suara aslinya.
#include <math.h>
#include <stdio.h>
#include <string.h>

#include <algorithm>
#include <string>
#include <vector>

#include <LovyanGFX.hpp>

#include "config.h"  // INTRO_ON_BOOT, SOUND_EFFECTS: bunyi sama dengan firmware
#include "earcon.h"
#include "scene.h"
#include "sound_cues.h"

namespace {

constexpr int FPS = 30;
constexpr int RATE = earcon::RATE;
LGFX_Sprite canvas;
std::string outDir;
bool withAudio = false;

void push(const scene::Rect &) {}

// Suara TTS (PCM 16 kHz mono) yang diputar mulai detik `at` di layar.
struct Voice {
  std::vector<int16_t> pcm;
  float at = 0;

  bool ok() const { return !pcm.empty(); }
  float seconds() const { return (float)pcm.size() / RATE; }
  // Keras suara (dBFS) blok 256 sampel yang sedang terdengar, seperti speaker::level().
  float level(float t) const {
    long start = lroundf((t - at) * RATE);
    if (start < 0 || start >= (long)pcm.size()) return -90;
    long end = start + 256 < (long)pcm.size() ? start + 256 : (long)pcm.size();
    float energy = 0;
    for (long i = start; i < end; i++) energy += (float)pcm[i] * pcm[i];
    return energy > 0 ? 10 * log10f(energy / (end - start) / (32768.0f * 32768.0f)) : -90;
  }
};

bool loadPcm(const std::string &path, std::vector<int16_t> &pcm) {
  FILE *f = fopen(path.c_str(), "rb");
  if (!f) return false;
  int16_t block[4096];
  size_t n;
  while ((n = fread(block, sizeof block[0], 4096, f)) > 0) pcm.insert(pcm.end(), block, block + n);
  fclose(f);
  return !pcm.empty();
}

// Paruh mengikuti suara: dihaluskan seperti display.cpp (naik cepat, turun pelan).
float smoothVoice(float &voiced, float raw) {
  float dt = 1.0f / FPS;
  voiced += (raw - voiced) * (1 - expf(-dt * (raw > voiced ? 40 : 12)));
  return voiced;
}

// Efek suara di detik `at` sejak layar mulai.
struct Timed {
  float at;
  earcon::Sound sound;
};

// Tambahkan bunyi dari sound_cues.h mulai detik `base`, seperti speaker::effects() di firmware:
// jadwal lama yang belum berbunyi diganti, bunyi yang sudah lewat > 250 ms dilewati.
void schedule(std::vector<Timed> &out, const cues::List &list, float base) {
  for (size_t i = out.size(); i-- > 0;)
    if (out[i].at >= base) out.erase(out.begin() + i);
  for (int i = 0; i < list.count; i++) {
    if (!SOUND_EFFECTS && list.items[i].sound != earcon::Sound::Attendance) continue;
    float at = base + list.items[i].at;
    if (at >= -0.25f) out.push_back({at < 0 ? 0 : at, list.items[i].sound});
  }
}

// Rekam satu layar selama `seconds`; update(ui, t) mengisi data tiap frame. Dengan audio: bunyi
// layar ini dari sound_cues.h (sama dengan firmware) dan suara `voice` dicampur ke <name>.pcm.
template <typename F>
void record(const char *name, float seconds, scene::Ui ui, F update, const Voice *voice = nullptr) {
  std::string path = outDir + "/" + name + ".rgb";
  FILE *out = fopen(path.c_str(), "wb");
  static uint8_t rgb[scene::W * scene::H * 3];
  int frames = 0;
  std::vector<Timed> sounds;
  bool doneCued = false;
  for (float t = 0; t < seconds; t += 1.0f / FPS, frames++) {
    ui.t = t;
    update(ui, t);
    if (frames == 0) {
      cues::List list = cues::forScreen(ui);
      schedule(sounds, list, list.fromWake ? -ui.wake : 0);
    }
    if (ui.done >= 0 && !doneCued) {
      doneCued = true;
      schedule(sounds, cues::bootDone(INTRO_ON_BOOT), t - ui.done);
    }
    scene::render(canvas, ui, frames == 0, push);
    canvas.readRectRGB(0, 0, scene::W, scene::H, rgb);
    fwrite(rgb, 1, sizeof rgb, out);
  }
  fclose(out);
  printf("%s: %d frame\n", name, frames);
  if (!withAudio) return;

  std::vector<int32_t> mix((size_t)frames * RATE / FPS, 0);
  auto add = [&](long at, const int16_t *s, long n) {
    for (long i = 0; i < n; i++)
      if (at + i >= 0 && at + i < (long)mix.size()) mix[at + i] += s[i];
  };
  bool hasVoice = voice && voice->ok();
  if (hasVoice) add(lroundf(voice->at * RATE), voice->pcm.data(), (long)voice->pcm.size());
  for (const Timed &c : sounds) {
    earcon::Player player(c.sound);
    std::vector<int16_t> s(player.length());
    player.read(s.data(), (int)s.size());
    long n = (long)s.size();
    if (hasVoice) {  // suara server didahulukan: efek terpotong saat suara mulai, tidak diputar selama suara
      if (c.at >= voice->at && c.at < voice->at + voice->seconds()) continue;
      if (c.at < voice->at) n = std::min(n, lroundf((voice->at - c.at) * RATE));
    }
    add(lroundf(c.at * RATE), s.data(), n);
  }
  std::vector<int16_t> pcm(mix.size());
  for (size_t i = 0; i < mix.size(); i++) pcm[i] = (int16_t)(mix[i] < -32768 ? -32768 : mix[i] > 32767 ? 32767 : mix[i]);
  FILE *a = fopen((outDir + "/" + name + ".pcm").c_str(), "wb");
  fwrite(pcm.data(), sizeof pcm[0], pcm.size(), a);
  fclose(a);
}

// Semua bunyi earcon.h berurutan (jeda 0,6 s) ke OUT/sounds.wav, untuk didengar satu per satu.
void writeSoundBoard() {
  std::vector<int16_t> pcm;
  for (int s = (int)earcon::Sound::Ready; s <= (int)earcon::Sound::Puff; s++) {
    earcon::Player player((earcon::Sound)s);
    size_t at = pcm.size();
    pcm.resize(at + player.length() + RATE * 6 / 10, 0);
    player.read(pcm.data() + at, player.length());
  }
  uint32_t bytes = (uint32_t)(pcm.size() * 2), rate = RATE, byteRate = RATE * 2, fmtSize = 16, riffSize = 36 + bytes;
  uint16_t pcmFormat = 1, channels = 1, align = 2, bits = 16;
  FILE *f = fopen((outDir + "/sounds.wav").c_str(), "wb");
  fwrite("RIFF", 1, 4, f), fwrite(&riffSize, 4, 1, f), fwrite("WAVEfmt ", 1, 8, f), fwrite(&fmtSize, 4, 1, f);
  fwrite(&pcmFormat, 2, 1, f), fwrite(&channels, 2, 1, f), fwrite(&rate, 4, 1, f), fwrite(&byteRate, 4, 1, f);
  fwrite(&align, 2, 1, f), fwrite(&bits, 2, 1, f), fwrite("data", 1, 4, f), fwrite(&bytes, 4, 1, f);
  fwrite(pcm.data(), 2, pcm.size(), f);
  fclose(f);
}

scene::Gesture gestureNamed(const char *name) {
  static const struct {
    const char *name;
    scene::Gesture gesture;
  } names[] = {{"wave", scene::Gesture::Wave},     {"happy", scene::Gesture::Happy},
               {"book", scene::Gesture::Book},     {"tasks", scene::Gesture::Tasks},
               {"button", scene::Gesture::Button}, {"cheer", scene::Gesture::Cheer}};
  for (const auto &n : names)
    if (!strcmp(n.name, name)) return n.gesture;
  return scene::Gesture::Talk;
}

// Kalimat perkenalan dari VOICE_DIR/intro.tsv (start<TAB>gesture<TAB>teks per baris).
bool loadIntro(const std::string &path, scene::Ui &ui) {
  FILE *f = fopen(path.c_str(), "r");
  if (!f) return false;
  char line[256];
  ui.segCount = 0;
  while (ui.segCount < scene::MAX_SEGMENTS && fgets(line, sizeof line, f)) {
    line[strcspn(line, "\r\n")] = 0;
    char *gesture = strchr(line, '\t');
    char *text = gesture ? strchr(gesture + 1, '\t') : nullptr;
    if (!text) continue;
    *gesture++ = 0;
    *text++ = 0;
    int i = ui.segCount++;
    ui.segStart[i] = strtof(line, nullptr);
    ui.segGesture[i] = gestureNamed(gesture);
    strncpy(ui.segText[i], text, sizeof ui.segText[i] - 1);
  }
  fclose(f);
  return ui.segCount > 0;
}

void copy(char *dst, size_t size, const char *src) {
  strncpy(dst, src, size - 1);
  dst[size - 1] = 0;
}

}  // namespace

int main(int argc, char **argv) {
  outDir = argc > 1 ? argv[1] : ".";
  withAudio = argc > 2;
  std::string voiceDir = withAudio ? argv[2] : "";
  canvas.setColorDepth(16);
  if (!canvas.createSprite(scene::W, scene::H)) return 1;
  scene::begin();

  // Suara TTS asli (make_voice.py). Bila belum ada: hanya efek suara, waktu bicara tiruan.
  Voice introVoice, answerVoice;
  scene::Ui introUi;
  bool realIntro = withAudio && loadPcm(voiceDir + "/intro.pcm", introVoice.pcm) &&
                   loadIntro(voiceDir + "/intro.tsv", introUi);
  if (withAudio) loadPcm(voiceDir + "/answer.pcm", answerVoice.pcm);
  if (withAudio && !(realIntro && answerVoice.ok()))
    printf("suara TTS belum lengkap di %s (jalankan make_voice.py): pakai waktu tiruan\n", voiceDir.c_str());

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
  record("home", 10.5f, ui, [](scene::Ui &, float) {});

  ui = scene::Ui();
  ui.kind = scene::Kind::Listen;
  float level = -90, lastLoud = -10;
  record("listen", 7.5f, ui, [&](scene::Ui &u, float t) {
    // diam -> bicara jelas -> bicara pelan (kurang jelas) -> diam lama (tidak ada suara)
    float raw = -62 + 3 * sinf(t * 5);
    if (t > 0.9f && t < 2.8f) raw = -28 + 7 * sinf(t * 7) * sinf(t * 2.3f);
    if (t > 2.8f && t < 4.6f) raw = -45 + 4 * sinf(t * 6) * sinf(t * 1.7f);
    level += (raw - level) * (raw > level ? 0.6f : 0.15f);
    if (raw >= scene::SPEECH_DBFS) lastLoud = t;
    u.level = level;
    u.quiet = t - lastLoud;
    u.elapsedMs = (uint32_t)(t * 1000) + 250;
  });

  ui = scene::Ui();
  ui.kind = scene::Kind::Think;
  record("think", 5.0f, ui, [](scene::Ui &u, float t) { u.elapsedMs = (uint32_t)(t * 1000); });

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
  if (answerVoice.ok()) {
    answerVoice.at = 0.6f;  // jawaban tampil dulu; suara menyusul (unduh + prebuffer)
    float voiced = -90;
    record("answer", answerVoice.at + answerVoice.seconds() + 1.5f, ui, [&](scene::Ui &u, float t) {
      u.speaking = t >= answerVoice.at && t < answerVoice.at + answerVoice.seconds();
      u.voice = smoothVoice(voiced, u.speaking ? answerVoice.level(t) : -90);
    }, &answerVoice);
  } else {
    record("answer", 6.0f, ui, [](scene::Ui &u, float t) {
      u.speaking = t < 3.5f;
      u.voice = u.speaking && sinf(t * 31) > -0.2f ? -22 : -60;
    });
  }

  ui = scene::Ui();
  ui.kind = scene::Kind::Notice;
  ui.tone = scene::Tone::Warn;
  copy(ui.title, sizeof ui.title, "Suara tidak terdengar");
  copy(ui.lines[0], sizeof ui.lines[0], "Coba bicara lebih dekat, ya.");
  copy(ui.lines[1], sizeof ui.lines[1], "Tahan tombol lalu bicara lagi");
  ui.lineCount = 2;
  record("no_speech", 4.0f, ui, [](scene::Ui &, float) {});

  ui = scene::Ui();
  ui.kind = scene::Kind::Notice;
  ui.tone = scene::Tone::Error;
  copy(ui.title, sizeof ui.title, "Gagal terhubung");
  copy(ui.lines[0], sizeof ui.lines[0], "Server tidak menjawab (timeout)");
  copy(ui.lines[1], sizeof ui.lines[1], "Tahan tombol untuk mencoba lagi");
  ui.lineCount = 2;
  record("error", 4.0f, ui, [](scene::Ui &, float) {});

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
  if (realIntro) {
    // kalimat, waktu, dan suara dari make_voice.py (sama dengan /v1/intro)
    introUi.kind = scene::Kind::Intro;
    introUi.duration = introVoice.seconds();
    introVoice.at = 0.5f;  // suara mulai setelah 0,5 s (unduh + prebuffer)
    float voiced = -90;
    record("intro", introVoice.at + introVoice.seconds() + 1.0f, introUi, [&](scene::Ui &u, float t) {
      u.position = t - introVoice.at;
      u.voice = smoothVoice(voiced, introVoice.level(t));
    }, &introVoice);
  } else record("intro", 13.4f, ui, [](scene::Ui &u, float t) {
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
  record("home_next", 6.0f, ui, [](scene::Ui &u, float t) { u.nowTs = NOW + (uint32_t)t; });

  ui = scene::Ui();
  ui.kind = scene::Kind::Home;
  ui.online = false;
  record("home_offline", 4.0f, ui, [](scene::Ui &, float) {});

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
  record("alert_hadir", 4.5f, ui, [](scene::Ui &u, float t) { u.nowTs = NOW + (uint32_t)t; });

  ui = scene::Ui();
  ui.kind = scene::Kind::Alert;
  ui.alert = scene::Alert::Deadline;
  copy(ui.alertCourse, sizeof ui.alertCourse, "Prak PV");
  copy(ui.alertDetail, sizeof ui.alertDetail, "Laporan Praktikum 5: Percabangan If-Else dan Select Case");
  copy(ui.alertWhen, sizeof ui.alertWhen, "Besok 23:59");
  ui.alertTo = NOW + 39 * 3600 - 60;
  record("alert_deadline", 4.0f, ui, [](scene::Ui &u, float t) { u.nowTs = NOW + (uint32_t)t; });

  ui = scene::Ui();
  ui.kind = scene::Kind::Portal;
  copy(ui.ssid, sizeof ui.ssid, "EduPad-Setup");
  copy(ui.password, sizeof ui.password, "edupad123");
  copy(ui.ip, sizeof ui.ip, "192.168.4.1");
  copy(ui.subtitle, sizeof ui.subtitle, "Kampus-WiFi");
  record("portal", 6.0f, ui, [](scene::Ui &, float) {});
  if (withAudio) writeSoundBoard();
  return 0;
}
