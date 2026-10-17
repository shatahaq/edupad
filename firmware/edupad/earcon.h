// Efek suara pendek EduPad (earcon) dan "suara" burung hantu (girang, bingung, menguap, ngorok,
// kaget, ...), dibangkitkan dari rumus tanpa file audio: PCM 16-bit mono 16 kHz seperti speaker.
// Tidak bergantung pada Arduino, jadi sama persis di firmware (speaker::effects) dan pratinjau di
// PC (trek suara `make video` di ../preview/new_ui_preview). Kapan dibunyikan: sound_cues.h.
#pragma once

#include <math.h>
#include <stdint.h>

namespace earcon {

constexpr int RATE = 16000;

enum class Sound : uint8_t {
  // nada antarmuka
  Ready,       // boot selesai ("Siap!"), hanya bila perkenalan dimatikan: arpeggio naik
  Listen,      // mulai merekam: "blip" naik
  Sent,        // tombol dilepas, rekaman terkirim: "blop" turun
  NoSpeech,    // suara tidak terdengar: dua nada lembut turun
  Error,       // gagal terhubung / galat: dua nada rendah
  Attendance,  // presensi dibuka: "ding-dong" (dulu speaker::chime())
  Attended,    // presensi tercatat: "ting-ting" naik, ceria
  Deadline,    // deadline dekat: "tok-tok"
  // burung hantu
  OwlHello,    // melambai: "hu-huu!"
  OwlHappy,    // girang: "yaay! hi-hi"
  OwlHop,      // lompatan kecil: "hup!"
  OwlConfused, // bingung: "hmm? huu?" (nada naik bertanya)
  OwlThink,    // berpikir: "hmm-mmm~"
  OwlStartle,  // kaget: "huu!?"
  OwlScared,   // kaget lalu gemetar: "huu!? uuu~"
  OwlShiver,   // menggigil: "brrr"
  OwlYawn,     // menguap: "hoaaa-mm"
  OwlSnore,    // ngorok: tarik napas "hrrrk", buang napas siulan "fiuuu"
  OwlStretch,  // menggeliat: "nnngh~ ah"
  Puff,        // mendarat / masuk selimut: "puf" lembut
};

// Bunyi `sound` pada detik `at` (dihitung dari awal layar / kejadian).
struct Cue {
  float at;
  Sound sound;
};

namespace detail {

// Warna suara: bobot harmoni ke-1..5.
enum class Timbre : uint8_t { Pure, Bell, Wood, Hoo, Ah, Hm };

inline const float *harmonics(Timbre t) {
  static const float table[][5] = {
      {1, 0, 0, 0, 0},              // Pure: siulan
      {1, 0.3f, 0, 0, 0},           // Bell: lonceng (harmoni oktaf)
      {1, 0, 0.4f, 0, 0},           // Wood: kayu / nada rendah tumpul
      {1, 0.18f, 0.05f, 0, 0},      // Hoo: vokal "uu" burung hantu
      {1, 0.55f, 0.35f, 0.2f, 0.1f},  // Ah: vokal terbuka "aa", cerah
      {1, 0.4f, 0.12f, 0.04f, 0},   // Hm: dengung mulut tertutup "mm"
  };
  return table[(int)t];
}

struct Part {
  float at, seconds;     // mulai dan lama (detik dari awal bunyi)
  float f0, f1, f2;      // nada di awal, tengah, akhir (Hz); diluncurkan halus
  float amp;             // puncak (dari 32767)
  float attack, release; // naik dan pudar (detik)
  float decay;           // peluruhan exp(-t * decay); 0 = ditahan
  Timbre timbre;
  float vib, vibRate;    // vibrato: nada * (1 + vib * sin), Hz
  float breath;          // campuran desah (noise) 0..1
  float trem, tremRate;  // getar keras suara (ngorok/menggigil) 0..1, Hz
};

// Nada lonceng/kayu: serangan 2,5 ms, meluruh, 8 ms terakhir dipudarkan.
inline Part tone(float at, float seconds, float freq, float freqEnd, float amp, float decay,
                 Timbre timbre = Timbre::Bell) {
  return {at, seconds, freq, (freq + freqEnd) / 2, freqEnd, amp, 0.0025f, 0.008f, decay, timbre,
          0, 0, 0, 0, 0};
}

// Suku kata burung hantu: nada f0 -> f1 -> f2, bentuk vokal `timbre`.
inline Part hoot(float at, float seconds, float f0, float f1, float f2, float amp, Timbre timbre,
                 float vib = 0, float vibRate = 6, float breath = 0.06f, float attack = 0.02f,
                 float release = -1, float trem = 0, float tremRate = 0) {
  return {at,     seconds, f0,     f1,      f2,     amp,  attack, release < 0 ? seconds * 0.35f : release,
          0,      timbre,  vib,    vibRate, breath, trem, tremRate};
}

constexpr int MAX_PARTS = 6;

struct Shape {
  Part parts[MAX_PARTS];
  int count;
};

inline Shape shape(Sound s) {
  using T = Timbre;
  switch (s) {
    case Sound::Ready:
      return {{tone(0.00f, 0.45f, 1046.5f, 1046.5f, 5500, 7), tone(0.08f, 0.45f, 1318.5f, 1318.5f, 5500, 7),
               tone(0.16f, 0.45f, 1568.0f, 1568.0f, 5500, 7), tone(0.24f, 0.55f, 2093.0f, 2093.0f, 5000, 6)},
              4};
    case Sound::Listen: return {{tone(0, 0.09f, 660, 1320, 7000, 8)}, 1};
    case Sound::Sent: return {{tone(0, 0.11f, 1320, 620, 7000, 8)}, 1};
    case Sound::NoSpeech:
      return {{tone(0.00f, 0.25f, 784.0f, 784.0f, 5000, 9), tone(0.14f, 0.32f, 659.3f, 659.3f, 5000, 8)}, 2};
    case Sound::Error:
      return {{tone(0.00f, 0.22f, 440.0f, 440.0f, 7000, 9, T::Wood), tone(0.17f, 0.38f, 349.2f, 349.2f, 7000, 7, T::Wood)},
              2};
    case Sound::Attendance:  // "ding-dong" seperti bel pintu: E6 lalu C6
      return {{tone(0.00f, 0.32f, 1318.5f, 1318.5f, 9000, 5.5f), tone(0.32f, 0.60f, 1046.5f, 1046.5f, 9000, 5.5f)}, 2};
    case Sound::Attended:
      return {{tone(0.00f, 0.13f, 1318.5f, 1318.5f, 7000, 6), tone(0.10f, 0.55f, 1760.0f, 1760.0f, 7000, 6)}, 2};
    case Sound::Deadline:
      return {{tone(0.00f, 0.18f, 880, 880, 8500, 18, T::Wood), tone(0.17f, 0.22f, 880, 880, 8500, 16, T::Wood)}, 2};

    case Sound::OwlHello:
      return {{hoot(0.00f, 0.16f, 560, 640, 600, 6500, T::Hoo),
               hoot(0.20f, 0.34f, 600, 780, 680, 6500, T::Hoo, 0.025f, 7)},
              2};
    case Sound::OwlHappy:
      return {{hoot(0.00f, 0.24f, 620, 980, 1060, 6500, T::Ah, 0.02f, 7, 0.05f),
               hoot(0.28f, 0.09f, 900, 1010, 950, 5000, T::Ah, 0, 6, 0.05f, 0.01f),
               hoot(0.40f, 0.13f, 950, 1120, 1000, 5000, T::Ah, 0, 6, 0.05f, 0.01f)},
              3};
    case Sound::OwlHop: return {{hoot(0, 0.09f, 520, 700, 760, 5500, T::Hoo, 0, 6, 0.1f, 0.01f)}, 1};
    case Sound::OwlConfused:
      return {{hoot(0.00f, 0.32f, 330, 320, 300, 5000, T::Hm, 0.015f, 5, 0.04f),
               hoot(0.36f, 0.36f, 420, 470, 690, 6000, T::Hoo, 0.02f, 6)},
              2};
    case Sound::OwlThink:
      return {{hoot(0.00f, 0.28f, 300, 330, 300, 4500, T::Hm, 0, 6, 0.04f),
               hoot(0.32f, 0.50f, 280, 360, 300, 4500, T::Hm, 0.02f, 5, 0.04f)},
              2};
    case Sound::OwlStartle:
      return {{hoot(0, 0.15f, 520, 1000, 1150, 7000, T::Ah, 0, 6, 0.1f, 0.01f)}, 1};
    case Sound::OwlScared:
      return {{hoot(0.00f, 0.13f, 520, 1000, 1100, 7000, T::Ah, 0, 6, 0.1f, 0.01f),
               hoot(0.15f, 0.55f, 760, 680, 520, 5500, T::Hoo, 0.06f, 11)},
              2};
    case Sound::OwlShiver:
      return {{hoot(0, 0.35f, 260, 250, 240, 3500, T::Hm, 0, 6, 0.3f, 0.02f, -1, 0.9f, 28)}, 1};
    case Sound::OwlYawn:
      return {{hoot(0.00f, 0.75f, 360, 520, 300, 6000, T::Ah, 0.015f, 5, 0.25f, 0.12f, 0.2f),
               hoot(0.68f, 0.35f, 280, 260, 220, 4000, T::Hm, 0, 6, 0.1f, 0.03f, 0.15f)},
              2};
    case Sound::OwlSnore:
      return {{hoot(0.0f, 0.9f, 95, 110, 100, 4500, T::Ah, 0, 6, 0.45f, 0.3f, 0.2f, 0.8f, 26),
               hoot(1.0f, 0.8f, 900, 1250, 1050, 2200, T::Pure, 0, 6, 0.35f, 0.25f, 0.35f)},
              2};
    case Sound::OwlStretch:
      return {{hoot(0.00f, 0.60f, 380, 560, 600, 5000, T::Hm, 0.03f, 8, 0.05f, 0.05f),
               hoot(0.60f, 0.18f, 620, 560, 480, 4500, T::Ah, 0, 6, 0.2f, 0.01f)},
              2};
    case Sound::Puff: {
      Part p = hoot(0, 0.18f, 120, 90, 70, 6000, T::Pure, 0, 6, 0.7f, 0.005f, 0.12f);
      p.decay = 10;
      return {{p}, 1};
    }
  }
  return {{}, 0};
}

constexpr float PI_F = 3.14159265f;

inline float smoothstep(float x) { return x * x * (3 - 2 * x); }

inline float pitch(const Part &p, float t) {
  float u = t / p.seconds;
  float f = u < 0.5f ? p.f0 + (p.f1 - p.f0) * smoothstep(u * 2) : p.f1 + (p.f2 - p.f1) * smoothstep(u * 2 - 1);
  return f * (1 + p.vib * sinf(2 * PI_F * p.vibRate * t));
}

inline float envelope(const Part &p, float t) {
  float env = fminf(1.0f, t / p.attack) * fminf(1.0f, (p.seconds - t) / p.release);
  if (p.decay > 0) env *= expf(-t * p.decay);
  if (p.trem > 0) env *= 1 - p.trem * (0.5f + 0.5f * sinf(2 * PI_F * p.tremRate * t));
  return env;
}

}  // namespace detail

// Memutar satu bunyi per blok (fase nada dan desah berlanjut antarblok).
class Player {
 public:
  explicit Player(Sound s) : shape_(detail::shape(s)) {
    float end = 0;
    for (int i = 0; i < shape_.count; i++) end = fmaxf(end, shape_.parts[i].at + shape_.parts[i].seconds);
    length_ = (int)(end * RATE);
  }

  int length() const { return length_; }

  // Isi out dengan sampel berikutnya, paling banyak n; 0 = bunyi selesai.
  int read(int16_t *out, int n) {
    if (n > length_ - pos_) n = length_ - pos_;
    for (int k = 0; k < n; k++, pos_++) {
      float time = (float)pos_ / RATE, v = 0;
      // desah: noise putih dihaluskan (~1,5 kHz) supaya lembut, bukan mendesis
      seed_ = seed_ * 1664525u + 1013904223u;
      noise_ += 0.25f * ((int32_t)seed_ * (1.0f / 2147483648.0f) - noise_);
      for (int i = 0; i < shape_.count; i++) {
        const detail::Part &p = shape_.parts[i];
        float t = time - p.at;
        if (t < 0 || t >= p.seconds) continue;
        phase_[i] += 2 * detail::PI_F * detail::pitch(p, t) / RATE;
        if (phase_[i] > 2 * detail::PI_F) phase_[i] -= 2 * detail::PI_F;
        const float *h = detail::harmonics(p.timbre);
        float wave = 0;
        for (int m = 0; m < 5; m++)
          if (h[m] > 0) wave += h[m] * sinf((m + 1) * phase_[i]);
        v += ((1 - p.breath) * wave + p.breath * 2.5f * noise_) * detail::envelope(p, t) * p.amp;
      }
      out[k] = (int16_t)fmaxf(-32768.0f, fminf(32767.0f, v));
    }
    return n;
  }

 private:
  detail::Shape shape_;
  int length_ = 0, pos_ = 0;
  float phase_[detail::MAX_PARTS] = {};
  float noise_ = 0;
  uint32_t seed_ = 12345;
};

// Panjang bunyi dalam sampel.
inline int length(Sound s) { return Player(s).length(); }

}  // namespace earcon
