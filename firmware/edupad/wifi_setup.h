// Wi-Fi: coba jaringan tersimpan lalu bawaan (secrets.h); bila gagal, hotspot pengaturan.
#pragma once

namespace wifisetup {

// true bila tersambung. `trying(ssid)` dipanggil sebelum tiap jaringan dicoba (untuk layar).
bool connect(void (*trying)(const char *ssid));
// Hotspot SETUP_AP_SSID + halaman di http://192.168.4.1 untuk memilih Wi-Fi. Tidak kembali:
// perangkat restart setelah Wi-Fi disimpan atau tombol ditekan (coba lagi).
[[noreturn]] void runPortal();

}  // namespace wifisetup
