// Salin menjadi secrets.h (tidak ikut git) lalu isi.
#pragma once

// Wi-Fi bawaan. Bila tidak tersambung, EduPad membuka hotspot "EduPad-Setup" untuk memilih
// Wi-Fi lain (lihat config.h); pilihan itu disimpan di flash dan dicoba lebih dulu.
#define WIFI_SSID "nama-wifi"
#define WIFI_PASSWORD "password-wifi"

// Server EduPad. Produksi: shata.id lewat HTTPS. Uji di jaringan lokal (python -m edupad serve
// --host 0.0.0.0): isi IP laptop, port 8000, EDUPAD_TLS 0.
#define EDUPAD_HOST "shata.id"
#define EDUPAD_PORT 443
#define EDUPAD_TLS 1

// Sama dengan EDUPAD_DEVICE_TOKEN di .env server.
#define EDUPAD_DEVICE_TOKEN "isi-token-perangkat"
