// Bunyi yang mengiringi tiap layar (earcon.h), diselaraskan dengan animasi scene.cpp UI baru
// (../preview/new_ui_preview): misalnya menguap saat burung hantu menguap. Dipakai firmware
// (display.cpp -> speaker::effects) dan pratinjau di PC, jadi video pratinjau = bunyi perangkat.
//
// Tidak ada bunyi selama merekam selain "blip" awal (mikrofon membisukan dirinya selama blip),
// selama suara jawaban/perkenalan diputar, dan di layar siap (tampil lama, jadi tetap hening).
#pragma once

#include "earcon.h"
#include "scene.h"

namespace cues {

struct List {
  const earcon::Cue *items;
  int count;
  bool fromWake;  // waktu dihitung dari saat dibangunkan (ui.wake = 0), bukan dari awal layar
};

template <int N>
List of(const earcon::Cue (&items)[N], bool fromWake = false) {
  return {items, N, fromWake};
}

// Bunyi untuk layar `ui` (kind, tone, alert, wake sudah diisi), dihitung dari awal layar.
inline List forScreen(const scene::Ui &ui) {
  using S = earcon::Sound;
  static const earcon::Cue boot[] = {{0.52f, S::Puff}, {1.45f, S::OwlHello}};  // mendarat, melambai
  static const earcon::Cue wake[] = {{0.02f, S::OwlStartle},   // kaget di ranjang ("!")
                                     {1.32f, S::OwlStretch},   // menggeliat
                                     {2.0f, S::OwlHello}};     // melambai
  static const earcon::Cue listen[] = {{0.0f, S::Listen}};
  static const earcon::Cue think[] = {{0.0f, S::Sent}, {0.45f, S::OwlThink}};
  static const earcon::Cue answer[] = {{0.12f, S::OwlHop}};  // melompat masuk dari kiri
  static const earcon::Cue warn[] = {{0.1f, S::OwlConfused}, {0.45f, S::NoSpeech}};  // nada saat "!" muncul
  static const earcon::Cue error[] = {{0.03f, S::OwlScared},  // terlonjak kaget
                                      {0.45f, S::Error},      // tanda silang muncul
                                      {2.2f, S::OwlShiver}};  // gemetar lagi
  static const earcon::Cue portal[] = {{0.12f, S::OwlHop}, {0.8f, S::OwlConfused}};
  static const earcon::Cue sleep[] = {{0.3f, S::OwlYawn},   // "Hoaam... aku ngantuk"
                                      {2.2f, S::Puff},      // masuk selimut
                                      {2.7f, S::OwlSnore},  // Z pertama naik
                                      {5.5f, S::OwlSnore}};
  static const earcon::Cue attendance[] = {{0.0f, S::Attendance}};
  static const earcon::Cue attended[] = {{0.12f, S::OwlHappy},  // lompatan pertama
                                         {0.4f, S::Attended},   // cap centang
                                         {1.07f, S::OwlHop}};   // lompatan kedua
  static const earcon::Cue deadline[] = {{0.0f, S::Deadline}};
  switch (ui.kind) {
    case scene::Kind::Boot: return of(boot);
    case scene::Kind::Home: return ui.wake >= 0 ? of(wake, true) : List{nullptr, 0, false};
    case scene::Kind::Listen: return of(listen);
    case scene::Kind::Think: return of(think);
    case scene::Kind::Answer: return of(answer);
    case scene::Kind::Notice:
      if (ui.tone == scene::Tone::Error) return of(error);
      if (ui.tone == scene::Tone::Warn) return of(warn);
      return {nullptr, 0, false};
    case scene::Kind::Portal: return of(portal);
    case scene::Kind::Sleep: return of(sleep);
    case scene::Kind::Alert:
      if (ui.alert == scene::Alert::Attendance) return of(attendance);
      if (ui.alert == scene::Alert::Attended) return of(attended);
      return of(deadline);
    case scene::Kind::Intro: break;  // suara perkenalan dari server
  }
  return {nullptr, 0, false};
}

// Saat boot selesai ("Siap!", burung hantu melompat girang). Nada siap hanya tanpa perkenalan:
// bila ada, suara perkenalan langsung menyusul.
inline List bootDone(bool intro) {
  static const earcon::Cue ready[] = {{0.0f, earcon::Sound::Ready}, {0.12f, earcon::Sound::OwlHappy}};
  return intro ? List{ready + 1, 1, false} : List{ready, 2, false};
}

}  // namespace cues
