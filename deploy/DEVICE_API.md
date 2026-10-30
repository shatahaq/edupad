# API perangkat ESP32

Alamat: `https://edupad.ai.id` (Cloudflare → Caddy → `python -m edupad serve` di `127.0.0.1:8000`;
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
X-Device-Heap: <byte>   X-Firmware: 1.3
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
  "timing": {"stt": 0.37, "agent": 2.63},
  "voice_mode": false
}
```

`voice_mode` dibaca setelah menjawab, jadi langsung berubah bila pertanyaan ini menyalakan atau
mematikan Mode Suara ("aktifkan mode suara"); saat aktif, `voice_clips` ikut dikirim (lihat
[Mode Suara](#mode-suara)).

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
- Firmware 1.6+ mengunduh **seluruh** badan ke PSRAM lebih dulu (batas `AUDIO_MAX_BYTES`)
  lalu memutarnya dari sana: memutar sambil mengunduh membuat suara patah-patah begitu Wi-Fi
  melambat sesaat. Suara karena itu mulai setelah TTS dan unduhan selesai, bukan pada potongan
  pertama. Tombol yang ditekan saat mengunduh membatalkannya.
- `?format=adpcm` (firmware 1.7+): IMA ADPCM 4-bit, **seperempat** ukuran PCM (8,25 KB per
  detik suara), dengan header `X-Audio-Format: adpcm_ima;rate=16000;channels=1;block=256`.
  Perangkat mengunduh hanya ±53 KB/detik (terukur 2026-10-23), jadi ukuran langsung menjadi
  jeda sebelum EduPad bicara. Format blok: header 4 byte (predictor int16 little-endian, index,
  1 byte kosong) + 128 byte nibble (rendah dulu) = 256 sampel; blok terakhir boleh lebih pendek.
  Encoder `src/edupad/voice/adpcm.py`, dekoder `firmware/edupad/adpcm.cpp`. Perangkat memutar
  sesuai `X-Audio-Format`, jadi server lama yang mengabaikan parameter ini tetap terdengar.
  Berlaku juga untuk `/v1/intro/audio`, `/v1/speech/*`, dan `/v1/voice/*`.
- TTS dimulai saat `/v1/ask` menjawab bila permintaan membawa `X-Firmware` (selalu dari
  perangkat), jadi suaranya sudah berjalan selagi layar tampil. Tanpa header itu (curl, tes)
  TTS baru jalan saat audio diminta, supaya uji manual tidak memakai kuota.
- Setelah suara jawaban mulai diputar, firmware 1.7+ mengirim sekali di permintaan berikutnya
  `X-Audio-Report: wait=<ms>;download=<ms>;bytes=<n>;format=adpcm|pcm`: jeda dari jawaban tampil
  sampai suara terdengar. Server mencatatnya di `logs/serve.log` (`[audio]`) dan `last_audio`
  status perangkat.
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
Saat tidur hanya `attendance` dan `deadline` yang membangunkan layar; jenis lain menunggu sampai
perangkat dibangunkan sendiri.

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
    berganti tiap hari, lalu tiap 15 menit sekali di 24 jam terakhir, jadi diingatkan lagi.
    Pengulangan 15 menit hanya berlaku bila data tugas sumber itu masih segar (kelas.usu < 1 jam,
    Classroom < 3 jam); di luar itu kembali sekali sehari, karena status "belum dikumpulkan" tidak
    bisa dipastikan lagi. `list_assignments` juga memberi `peringatan` saat datanya lewat ambang.
  - `attended`: presensi pertemuan yang sedang berlangsung sudah tercatat "hadir" (mis. diisi
    otomatis oleh cron `attendance --fill`).
  - `warning` (hanya bila permintaan membawa `X-Firmware`): peringatan dini Equity Radar, yaitu
    jatah tidak hadir hampir/sudah habis atau anggaran keuangan >= 90%; `level` `high`/`medium`.
  - `review` (hanya dengan `X-Firmware`, pukul 16-21 WIB): topik kuis Tutor yang jatuh tempo
    diulang; `when` berisi "Penguasaan 40%". Tahan tombol lalu ucapkan "uji aku lagi".
  - Isi kartu tambahan dihitung di `src/edupad/agent/radar.py` (cache 5 menit).
- `stale`: sumber yang sesinya habis (`SATU`, `kelas.usu`); perangkat menampilkan peringatan.
- Semua teks ASCII (font LCD). Isinya disusun di `src/edupad/agent/updates.py`.
- Tiap pemberitahuan juga membawa `speech` (kalimat untuk dibacakan) dan `voice_mode` ada di
  tingkat atas; saat Mode Suara aktif tiap pemberitahuan mendapat `audio_url` dan jawaban
  memuat `voice_clips` (lihat bagian berikut). `attendance` dan `deadline` mendapat `audio_url`
  walau Mode Suara mati: perangkat memutar `audio_url` apa pun yang dikirim, tanpa memeriksa
  status Mode Suara.

## Mode Suara

EduPad bisa dipakai tanpa melihat layar, dirancang untuk mahasiswa tunanetra
(`src/edupad/voice/mode.py`). Dinyalakan lewat suara ("aktifkan mode suara", "bicara lebih
cepat") atau dashboard (Pengaturan); disimpan di `data/device/voice_mode.json`.

- Jawaban AI memuat seluruh isi dalam `speech` (hingga ~900 karakter), tanpa merujuk ke layar,
  dan menawarkan "mau dilanjutkan?" untuk penjelasan panjang. Kecepatan bicara (`lambat`,
  `normal`, `cepat`, `sangat_cepat`) berlaku untuk semua suara jawaban.
- `GET /v1/speech/{kunci}`: suara satu pemberitahuan (PCM seperti `/v1/audio`, `?format=wav`
  untuk laptop). Kunci = hash teks + kecepatan, sehingga pemberitahuan yang sama hanya sekali
  memakai kuota TTS.
- Perintah setelan ("aktifkan/matikan mode suara", "bicara lebih cepat/lambat") dijawab `/v1/ask`
  langsung dari `src/edupad/voice/commands.py`, tanpa memanggil agent: bentuk responsnya sama
  (`status`, `speech`, `screen`, `audio_url`), hanya `audio_url`-nya menunjuk
  `GET /v1/voice/reply/{nama}` yang PCM-nya sudah tersimpan di disk. Jadi perintah ini tidak
  memakai token LLM maupun kuota TTS, dan tidak masuk riwayat percakapan. Kecepatan bergerak satu
  tingkat per perintah. Ucapan yang tidak persis cocok (mis. "apa itu mode suara?") tetap
  diteruskan ke agent, yang masih punya tool `set_voice_mode`.
- `GET /v1/voice/clip/{nama}`: pesan status yang disimpan perangkat di PSRAM dan diputar sendiri,
  sehingga tetap terdengar saat Wi-Fi atau server putus: `ready`, `wifi`, `send`, `server`,
  `error`, `no_speech`, `audio`, `no_answer`, `new_session` (teks di `src/edupad/voice/clips.py`).
  `voice_clips` berisi alamat masing-masing dengan `?v=`; nilainya berganti bila suara, bahasa,
  atau kecepatan berubah, tanda perangkat perlu mengunduh ulang. Isinya ditampung di PSRAM, jadi
  diunduh sekali tiap kali perangkat menyala. `ready` ("EduPad siap, tahan tombol lalu tanya
  saja") diputar firmware 1.5 saat perangkat dibangunkan dari tidur.
- Firmware 1.2 (`firmware/edupad/voice.cpp`): bunyi naik saat mulai merekam, bunyi turun saat
  rekaman terkirim, ketukan pelan tiap 2 detik selama menunggu jawaban, semua pemberitahuan
  berbunyi lalu dibacakan (di luar Mode Suara hanya presensi dibuka dan deadline tugas yang
  berbunyi dan dibacakan), dan pesan status di atas untuk setiap kegagalan. Status Mode Suara
  disimpan di NVS, jadi bunyi penanda tetap ada walau server belum terjangkau saat menyala.

## Bahasa

EduPad bisa berbahasa Indonesia (bawaan) atau Inggris (`src/edupad/voice/lang.py`); disimpan di
`data/device/language.json` dan diganti lewat suara ("switch to English", "ganti ke bahasa
Indonesia"), tool `set_language`, atau `PUT /api/office/language` dari dashboard.

- `/v1/updates` dan `/v1/ask` memuat `language` (`"id"` / `"en"`) di tingkat atas. Firmware
  (`firmware/edupad/lang.cpp`) menyimpannya di flash dan memakainya untuk semua teks bawaan layar,
  termasuk layar nyala dan pesan galat sebelum server terhubung.
- Label dan kalimat pemberitahuan `/v1/updates` ikut bahasa itu: `day` ("Besok" / "Tomorrow"),
  `when` ("Tutup 10:40" / "Closes 10:40", "Penguasaan 40%" / "Mastery 40%"), `detail` kartu
  peringatan, dan `speech`.
- Satu setelan mengubah semuanya: bahasa pengenalan suara (Whisper `language` + kosakata),
  `language_code` TTS, bahasa jawaban agent (`speech`, `screen`, `detail`), kalimat tetap
  Mode Suara (`/v1/voice/clip/*`, `/v1/voice/reply/*`), dan naskah perkenalan `/v1/intro`.
- Perintah ganti bahasa dijawab tanpa LLM (`src/edupad/voice/commands.py`), dan konfirmasinya
  sudah memakai bahasa yang baru.
- Suara yang sudah dibuat per bahasa tetap disimpan (`data/voice/clips/`,
  `data/voice/intro/intro-en.pcm`), jadi berpindah bahasa bolak-balik tidak memakai kuota TTS.
- Nama mata kuliah, dosen, dan judul materi tetap seperti aslinya (bahasa Indonesia) walau
  jawabannya bahasa Inggris.

## GET /v1/health

`{"status": "ok"}` tanpa token; untuk cek koneksi saat perangkat menyala.

## Uji dari laptop (tanpa ESP32)

```bash
TOKEN=...   # isi EDUPAD_DEVICE_TOKEN
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
     -d '{"text": "tugas apa saja minggu ini?"}' https://edupad.ai.id/v1/ask
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: audio/wav" \
     --data-binary @rekaman.wav https://edupad.ai.id/v1/ask
curl -s -H "Authorization: Bearer $TOKEN" -o jawaban.wav "https://edupad.ai.id/v1/audio/<id>?format=wav"
```
