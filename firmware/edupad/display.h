// Tampilan LCD 480x320 (landscape) beranimasi. Semua layar digambar terus-menerus oleh task di
// latar (gambarnya di scene.cpp); fungsi di sini hanya mengganti layar atau datanya, jadi cepat
// dan aman dipanggil dari loop rekam/putar (kecuali bootDone, yang menunggu animasi selesai).
#pragma once

#include <ArduinoJson.h>

namespace display {

enum class Tone : uint8_t { Info, Warn, Error };

// Menyalakan LCD dan langsung memulai layar nyala (burung hantu jatuh, bangun, melambai).
void begin();
// Teks dan kemajuan (0..1) di layar nyala.
void bootStep(const char *text, float progress);
// Burung hantu melompat senang + "Siap!" (~1 s); kembali setelah animasinya selesai.
void bootDone();

// Layar siap: petunjuk cara bertanya. newSession: tampilkan "Topik baru dimulai".
void idle(bool newSession);
// Tertidur (menguap, berselimut, Zzz) lalu layar meredup. Untuk saat lama tidak ada pertanyaan.
void sleep();
// Dibangunkan: kaget di ranjang, melompat keluar selimut, menggeliat, lalu melambai di layar
// siap. Bila setelah itu langsung merekam, layar mendengarkan menampilkan kaget sebentar.
void wake();
// Status Wi-Fi; saat terputus layar siap menampilkan peringatan.
void setOnline(bool online);
// Dipanggil berulang selama merekam (level mikrofon menggerakkan batang suara).
void recording(uint32_t elapsedMs, float levelDbfs);
// Dipanggil berulang selama menunggu jawaban server.
void processing(uint32_t elapsedMs);
// Jawaban /v1/ask: `screen` {title, lines[]}, `status` "ok" / "no_speech" / "error".
// `question` (hasil pengenalan suara) boleh kosong.
void answer(JsonObjectConst screen, const char *question, const char *status);
// Burung hantu "bicara" selama suara jawaban diputar.
void speaking(bool on);
// Dipanggil tiap potongan suara diputar: keras suara (dBFS, menggerakkan paruh) dan lama
// suara yang sudah terdengar (ms, menyelaraskan teks perkenalan).
void voice(float levelDbfs, uint32_t positionMs);
// Perkenalan diri: `segments` dari /v1/intro [{start, gesture, text}], `duration` detik.
// Kalimat dan gerakan berganti mengikuti voice(); tampil sampai layar lain dipanggil.
void intro(JsonArrayConst segments, float duration);
// Pesan singkat: judul + hingga dua baris keterangan.
void message(const char *title, const char *line1 = nullptr, const char *line2 = nullptr,
             Tone tone = Tone::Info);
// Petunjuk hotspot pengaturan Wi-Fi. `failed`: jaringan yang gagal disambung (boleh kosong).
void portal(const char *apSsid, const char *apPassword, const char *ip, const char *failed);
// Jam dari server (detik epoch), untuk hitung mundur kuliah, presensi, dan deadline.
void clock(uint32_t nowTs);
// Dari /v1/updates: `next` = kuliah berikutnya (null bila tidak ada), `stale` = sumber data
// yang sesinya habis (peringatan di layar siap).
void schedule(JsonObjectConst next, JsonArrayConst stale);
// Pemberitahuan dari /v1/updates (presensi dibuka / tercatat, deadline). Tampil sampai layar
// lain dipanggil; app yang mengatur lamanya.
void alert(JsonObjectConst alert);
// Notifikasi kecil di bawah layar selama beberapa detik, di atas layar apa pun.
void toast(const char *text);

}  // namespace display
