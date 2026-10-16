# API perangkat ESP32

Alamat: `https://shata.id` (Cloudflare → Caddy → `python -m edupad serve` di `127.0.0.1:8000`;
kode di `src/edupad/server.py`). ESP32 memakai HTTPS: `esp_http_client` dengan
`crt_bundle_attach = esp_crt_bundle_attach`.
Semua permintaan selain `/v1/health` wajib membawa header:

```
Authorization: Bearer <EDUPAD_DEVICE_TOKEN>
```

Firmware 1.1+ juga mengirim status perangkat (dicatat ke `data/device/status.json` untuk
dashboard Monitoring → Perangkat):

```
X-Device-Id: <MAC>      X-Device-RSSI: -61      X-Device-Uptime: <detik>
X-Device-Heap: <byte>   X-Firmware: 1.1
```

## Alur satu pertanyaan

```
tombol ditekan ──► rekam PCM ──► POST /v1/ask ──► tampilkan `screen` di LCD
                                              └─► audio_url? ──► GET audio_url ──► putar ke I2S
```

1. Rekam mikrofon: **PCM 16-bit signed little-endian, mono, 16 kHz** (32.000 byte/detik).
2. `POST /v1/ask` dengan rekaman sebagai badan. Bisa dikirim **sambil merekam** dengan
   `Transfer-Encoding: chunked` (esp_http_client: `esp_http_client_open(client, -1)` lalu
   `esp_http_client_write` per potongan, tutup dengan chunk kosong), atau sekaligus dengan
   `Content-Length`.
3. Tampilkan `screen`, lalu bila `audio_url` tidak `null`, `GET` URL itu di koneksi yang sama
   (keep-alive) dan putar byte-nya langsung ke I2S begitu datang.

## POST /v1/ask

| Header `Content-Type` | Badan |
|---|---|
| `application/octet-stream` (atau kosong) | PCM mentah seperti di atas |
| `audio/wav` | File WAV |
| `application/json` | `{"text": "pertanyaan"}`, untuk uji tanpa mikrofon |

`?new=1` memulai sesi percakapan baru (mis. tombol ditekan lama). Batas rekaman 120 detik.

Jawaban **selalu** JSON dengan `status` dan `screen`, termasuk saat error, sehingga firmware
cukup punya satu jalur tampilan:

```json
{
  "status": "ok",
  "question": "Pertemuan 5 PV tentang apa?",
  "speech": "Pertemuan lima Pemrograman Visual membahas percabangan If-Else, ...",
  "screen": {
    "title": "PV Pertemuan 5: If-Else",
    "title_size": "large",
    "lines": ["- Percabangan If-Else", "- ElseIf dan Nested If", "- Operator: And, Or, Not"]
  },
  "audio_url": "/v1/audio/1U_sndi5W3cq",
  "timing": {"stt": 0.37, "agent": 2.63}
}
```

Latensi (uji lokal, rekaman dikirim real-time): akhir bicara -> layar ~3,0 s (terukur),
-> suara pertama ~4,0 s (layar + audio pertama TTS ~0,95 s yang terukur terpisah). Supaya tetap cepat, kirim rekaman **sambil merekam** (chunked):
server memuat memory dan membuka koneksi ke Groq/DeepSeek/ElevenLabs selama pengguna bicara.

- `screen.title`: maks. 38 karakter; `title_size` `"large"` (font 2x, maks. 24 karakter) atau
  `"normal"`. `screen.lines`: maks. 9 baris x 38 karakter, sudah dibungkus dan hanya ASCII.
- `status` lain:

| HTTP | `status` | Arti | Yang dilakukan perangkat |
|---|---|---|---|
| 200 | `no_speech` | Rekaman hening / terlalu pendek; agent tidak dipanggil | Tampilkan `screen` ("Suara tidak terdengar") |
| 400 / 413 | `error` | Permintaan salah / rekaman terlalu besar | Tampilkan `screen`; bug firmware |
| 401 | `error` | Token salah | Tampilkan `screen`; periksa token |
| 502 | `error` | Groq / DeepSeek / ElevenLabs gagal | Tampilkan `screen`; boleh coba lagi |
| 500 | `error` | Bug server (lihat `logs/serve.log`) | Tampilkan `screen` |

Field `error` berisi penyebab teknis untuk log serial, bukan untuk LCD.

## GET /v1/audio/{id}

- Badan: PCM 16-bit signed little-endian, mono, 16 kHz, dialirkan per potongan
  (`Transfer-Encoding: chunked`); header `X-Audio-Format: pcm_s16le;rate=16000;channels=1`.
  Server hanya mengirim sampel utuh, tetapi `esp_http_client_read` bisa mengembalikan jumlah
  byte ganjil: simpan sisa 1 byte untuk dibaca berikutnya sebelum menulis ke I2S.
- Bila koneksi putus sebelum chunk penutup, audio tidak utuh (TTS gagal di tengah).
- Hanya suara **jawaban terakhir** yang disimpan (di memori server); jawaban baru menimpanya
  dan id lamanya menjadi 404. Putar ulang (`GET` URL yang sama, atau `GET /v1/audio/latest`
  bila perangkat tidak lagi tahu URL-nya, mis. setelah restart) diambil dari simpanan tanpa
  kuota TTS. Bila perangkat memutus koneksi di tengah pemutaran, server tetap menyelesaikan
  dan menyimpan audionya.
- `?format=wav` mengembalikan WAV utuh, untuk didengar di laptop.
- 404 bila id tidak dikenal / sudah diganti jawaban baru (atau `latest` sebelum ada jawaban); 502 bila TTS gagal sebelum audio pertama.

## GET /v1/intro dan /v1/intro/audio

Perkenalan diri yang diputar perangkat setiap menyala (setelah `/v1/health`).

```json
{
  "duration": 12.4,
  "audio_url": "/v1/intro/audio",
  "segments": [
    {"start": 0.0, "gesture": "wave", "text": "Halo! Aku EduPad."},
    {"start": 1.6, "gesture": "happy", "text": "Teman belajarmu."}
  ]
}
```

- `segments`: tiap kalimat dengan waktu mulainya (detik dari awal audio) dan gerakan burung
  hantu di layar (`wave`, `happy`, `book`, `tasks`, `button`, `cheer`; lainnya = bicara saja).
  Naskahnya ada di `src/edupad/voice/intro.py`.
- `/v1/intro/audio`: PCM seperti `/v1/audio`, utuh dengan `Content-Length`; `?format=wav`
  untuk didengar di laptop.
- Suara dibuat **sekali** lewat TTS lalu disimpan di `data/voice/intro/`; permintaan
  berikutnya tidak memakai kuota. Dibuat ulang otomatis hanya bila naskah atau suara berubah.
  Permintaan pertama menunggu TTS (beberapa detik); buat lebih dulu dengan
  `python -m edupad intro` (juga menyimpan `intro.wav` untuk didengar).
- 502 bila TTS gagal saat membuat suara (perangkat melewati perkenalan).

## GET /v1/updates

Dicek perangkat tiap 2 menit saat menganggur (juga saat tidur), hanya membaca data hasil cron.

```json
{
  "now_ts": 1792040400,
  "next_class": {"name": "Prak EA", "course": "Praktikum E-Application", "room": "Laboratorium Komputer",
                 "room_code": "I09.3.3.2", "day": "Besok", "time": "08:00",
                 "start_ts": 1792026000, "end_ts": 1792032000, "ongoing": false},
  "alerts": [
    {"id": "att:6a96...", "kind": "attendance", "course": "Statistika", "detail": "Ruang 3.2",
     "when": "Tutup 09:20", "method": "qr", "from_ts": 1792039800, "to_ts": 1792041600}
  ],
  "stale": ["SATU"]
}
```

- `now_ts`: jam server (detik epoch) untuk hitung mundur di perangkat, tanpa NTP.
- `next_class`: kelas yang sedang berlangsung atau mulai paling dekat (jadwal KRS mingguan); `null`
  bila tidak ada. `name` nama singkat dari alias katalog ("Prak MSBD").
- `alerts` (paling banyak 5, terpenting dulu), `id` stabil supaya tiap pemberitahuan tampil sekali:
  - `attendance`: presensi sedang dibuka dan belum diisi (`method` `qr` / `direct`); hanya bila
    data presensi berumur < 15 menit.
  - `deadline`: tugas belum dikumpulkan (kelas.usu dan Classroom) dengan deadline < 48 jam; `id`
    berganti tiap hari dan saat tinggal < 3 jam, jadi diingatkan lagi.
  - `attended`: presensi pertemuan yang sedang berlangsung sudah tercatat "hadir" (mis. diisi
    otomatis oleh cron `attendance --fill`).
  - `warning` (hanya bila permintaan membawa `X-Firmware`): peringatan dini Equity Radar, yaitu
    jatah tidak hadir hampir/sudah habis atau anggaran keuangan >= 90%; `level` `high`/`medium`.
  - `review` (hanya dengan `X-Firmware`, pukul 16-21 WIB): topik kuis Tutor yang jatuh tempo
    diulang; `when` berisi "Penguasaan 40%". Tahan tombol lalu ucapkan "uji aku lagi".
  - Isi kartu tambahan dihitung di `src/edupad/agent/radar.py` (cache 5 menit).
- `stale`: sumber yang sesinya habis (`SATU`, `kelas.usu`); perangkat menampilkan peringatan.
- Semua teks ASCII (font LCD). Isinya disusun di `src/edupad/agent/updates.py`.

## GET /v1/health

`{"status": "ok"}` tanpa token; untuk cek koneksi saat perangkat menyala.

## Uji dari laptop (tanpa ESP32)

```bash
TOKEN=...   # isi EDUPAD_DEVICE_TOKEN
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
     -d '{"text": "tugas apa saja minggu ini?"}' https://shata.id/v1/ask
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: audio/wav" \
     --data-binary @rekaman.wav https://shata.id/v1/ask
curl -s -H "Authorization: Bearer $TOKEN" -o jawaban.wav "https://shata.id/v1/audio/<id>?format=wav"
```
