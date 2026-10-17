# UI baru EduPad (gaya Duolingo) + efek suara

Eksperimen tampilan baru dan suara burung hantu, dengan pratinjau di PC (GIF dan video bersuara)
sebelum dipasang di perangkat. Isinya ada dua jenis: file untuk perangkat dan alat pratinjau.

| | Status |
|---|---|
| Efek suara (nada + burung hantu) | **Sudah tersambung di firmware** (`firmware/edupad/`), lolos kompilasi ESP32-S3, belum dicoba di perangkat |
| UI baru (`scene.cpp` di folder ini) | **Belum dipindah** ke firmware (masih UI lama), tetapi sudah dicoba dikompilasi bersama firmware: lolos, 1,36 MB (43% partisi 3 MB) |

Kompilasi dicek dengan arduino-cli, core esp32 3.3.12, FQBN
`esp32:esp32:esp32s3:PSRAM=opi,FlashSize=16M,PartitionScheme=app3M_fat9M_16MB`. Satu-satunya
peringatan adalah API I2S lama (`driver/i2s.h`) di `mic.cpp`/`speaker.cpp` yang sudah ada sebelumnya.
| Suara TTS ElevenLabs | Di **server**, bukan di perangkat (lihat [ElevenLabs](#elevenlabs)) |

## Isi folder

| File | Untuk | Fungsi |
|---|---|---|
| `scene.cpp` | **perangkat** | Semua layar dan animasi UI baru. Pengganti `firmware/edupad/scene.cpp` (interface `scene.h` sama, `display.cpp` tidak perlu diubah) |
| `new_ui_fonts.h` | **perangkat** | Font Nunito untuk `scene.cpp` (dibuat dari `../../tools/fonts/Nunito.ttf`, lihat `Makefile`) |
| `preview.cpp` | PC | Menjalankan `scene.cpp` dengan data tiruan, merekam frame + trek suara tiap layar |
| `make_video.py` | PC | Frame + suara -> `out/<layar>.mp4` dan `out/demo.mp4` (semua layar berurutan) |
| `make_voice.py` | PC | Membuat suara TTS asli (perkenalan + jawaban contoh) untuk video lewat modul TTS server |
| `Makefile` | PC | `make` (GIF) dan `make video` (GIF + video bersuara) |
| `voice/`, `out/`, `out_dark/`, `build/` | PC | Hasil; tidak masuk git |

Efek suara sendiri tidak di folder ini, tetapi di firmware, dan dipakai bersama oleh pratinjau:

| File | Isi |
|---|---|
| `firmware/edupad/earcon.h` | **Bentuk** semua bunyi: dibangkitkan dari rumus (tanpa file audio), PCM 16 kHz |
| `firmware/edupad/sound_cues.h` | **Kapan** bunyi diputar: daftar bunyi per layar, diselaraskan dengan animasi UI baru |

Karena tabelnya satu, yang terdengar di `out/*.mp4` sama dengan yang diputar perangkat.

## Efek suara

### Daftar bunyi per layar (`sound_cues.h`)

| Layar | Bunyi (detik sejak layar muncul) |
|---|---|
| Boot | `Puff` 0,52 (mendarat), `OwlHello` 1,45 (melambai); saat siap `OwlHappy` (+ `Ready` bila `INTRO_ON_BOOT` 0) |
| Bangun dari tidur | `OwlStartle` 0,02 (kaget di ranjang), `OwlStretch` 1,32 (menggeliat), `OwlHello` 2,0 |
| Rekam (listen) | `Listen` 0 ("blip"); mikrofon dibisukan selama blip |
| Berpikir (think) | `Sent` 0 ("blop"), `OwlThink` 0,45 ("hmm-mmm~") |
| Jawaban | `OwlHop` 0,12 (melompat masuk), lalu suara jawaban dari server |
| Pesan peringatan (mis. suara tidak terdengar) | `OwlConfused` 0,1 ("hmm? huu?"), `NoSpeech` 0,45 |
| Pesan galat | `OwlScared` 0,03 (kaget + gemetar), `Error` 0,45, `OwlShiver` 2,2 ("brrr") |
| Tidur | `OwlYawn` 0,3 ("hoaaa-mm"), `Puff` 2,2 (selimut), `OwlSnore` 2,7 dan 5,5 (ngorok) |
| Presensi dibuka | `Attendance` 0 ("ding-dong", pengganti `speaker::chime()` lama) |
| Presensi tercatat | `OwlHappy` 0,12, `Attended` 0,4 (cap centang), `OwlHop` 1,07 |
| Deadline | `Deadline` 0 ("tok-tok") |
| Wi-Fi portal | `OwlHop` 0,12, `OwlConfused` 0,8 |
| Layar siap, perkenalan | hening (layar siap tampil lama; perkenalan sudah bersuara TTS) |

Dengarkan semua bunyi berurutan di `out/sounds.wav` (dibuat `make video`), atau per layar di
`out/<layar>.mp4`.

### Cara kerjanya di firmware

```
display.cpp uiTask: layar baru / boot selesai
  -> cues::forScreen(ui)          (sound_cues.h)
  -> speaker::effects(cues, base) (jadwal; menggantikan jadwal lama)
       -> task "effects" (core 1): earcon::Player per blok 256 sampel -> I2S
```

Aturan yang dijaga:

- **Suara dari server didahulukan.** Begitu `speaker::write()` dipanggil, efek berhenti di blok
  berikutnya dan tidak diputar sampai `finish()`/`stop()`.
- **Tidak ada bunyi yang ikut terekam.** Selama merekam hanya ada "blip" awal, dan selama bunyi
  diputar `mic::mute()` merekam hening (dan meter tidak bergerak). Bisu hanya berlaku saat sedang
  merekam dan direset oleh `mic::start()`.
- **Layar berganti = jadwal diganti.** Bunyi layar lama yang belum terdengar dibatalkan; bunyi yang
  terlambat > 250 ms dilewati (misalnya bagian "kaget di ranjang" saat dibangunkan sebelum masuk
  kamar).
- **Tidak menahan tombol.** Bunyi diputar task latar, `loop()` tidak menunggu.
- `SOUND_EFFECTS 0` di `config.h`: hening (misalnya di kelas), kecuali bunyi presensi dibuka.

### Mengubah bunyi

- Bentuk bunyi: `shape()` di `earcon.h`. Bunyi burung hantu memakai
  `hoot(mulai, lama, nada_awal, nada_tengah, nada_akhir, keras, vokal, vibrato, laju_vibrato, desah, ...)`,
  dengan vokal `Hoo` ("uu"), `Ah` ("aa"), `Hm` ("mm"), atau `Pure` (siulan). Nada antarmuka memakai `tone(...)`.
- Waktu bunyi: tabel di `sound_cues.h`. Waktunya mengikuti animasi `scene.cpp` UI **baru**; dengan
  UI lama gerakannya tidak selalu pas.
- Lalu `make video` dan dengarkan `out/sounds.wav` / `out/demo.mp4`.

## ElevenLabs

```
ESP32 --rekaman--> server (Groq STT -> agent -> ElevenLabs TTS) --PCM 16 kHz--> speaker ESP32
```

- API key ElevenLabs hanya di `.env` server (`src/edupad/voice/tts.py`). **Jangan** taruh key di
  firmware; perangkat cukup memutar `audio_url` dari server.
- Perkenalan saat menyala diambil dari `GET /v1/intro` (`src/edupad/voice/intro.py`). Endpoint ini
  ada di branch `esp32-voice`, **belum** di `feat/dashboard`; server harus memilikinya, kalau
  tidak perkenalan dilewati.
- `make_voice.py` di folder ini hanya untuk video pratinjau (meniru yang dilakukan server).

## Membuat pratinjau (PC)

Butuh Linux/WSL dengan `g++`, `make`, `python3` + Pillow, `ffmpeg`, dan LovyanGFX di
`~/Arduino/libraries/LovyanGFX` (atau `make LGFX=/path/ke/LovyanGFX/src`).

```sh
make          # out/*.gif + *.png (terang) dan out_dark/ (gelap)
make video    # juga out/*.mp4, out/demo.mp4, out/sounds.wav (terang dan gelap)
```

Suara TTS untuk video dibuat sekali (dari root repo, butuh paket `edupad` dan `.env` berisi
`API_KEY_ElevenLabs`/`Voice_ID_ElevenLabs`; kuota hanya terpakai bila naskah/suara berubah):

```sh
python firmware/preview/new_ui_preview/make_voice.py
```

Tanpa `voice/`, `make video` tetap jalan dengan efek suara saja dan waktu bicara tiruan.

## Memindahkan UI baru ke perangkat

1. Salin `scene.cpp` dan `new_ui_fonts.h` ke `firmware/edupad/` (menimpa `scene.cpp` lama).
   Untuk tema gelap, tambahkan `#define NEW_UI_DARK 1` di baris paling atas `scene.cpp`.
2. Flash dengan partisi **16M Flash (3MB APP/9.9MB FATFS)** dan **OPI PSRAM** (lihat
   [../../README.md](../../README.md)); font dan animasi menambah ukuran sketch.
3. Uji di perangkat, terutama yang di bawah ini.

### Belum diuji di perangkat / risiko

- **Kelancaran layar (paling penting).** `scene.cpp` baru menggambar ulang dan mengirim **seluruh
  layar tiap frame** (`push({0, 0, W, H})` di akhir `render()`); `scene.cpp` lama hanya mengirim
  area yang berubah. Pada SPI 40 MHz satu layar penuh 480x320 16 bit butuh ~61 ms untuk dikirim
  (maks. ~16 fps sebelum waktu menggambar), dan kanvasnya di PSRAM. Bila tersendat atau
  mengganggu rekaman/jaringan: batasi `push()` ke area yang bergerak, seperti `scene.cpp` lama.
- **Efek suara** sudah lolos kompilasi ESP32, tetapi belum didengar di speaker asli: cek keras
  suara relatif terhadap suara jawaban, dan bahwa "blip" rekam tidak terdengar di transkrip.
- Beban CPU sintesis efek (beberapa `sinf` per sampel di core 1) belum diukur di perangkat.

### Daftar uji

- [ ] Menyala: "puf" saat mendarat, "hu-huu!" saat melambai, girang saat siap, lalu perkenalan bersuara
- [ ] Tahan tombol: "blip", bicara, lepas: "blop" + "hmm"; transkrip tidak berisi bunyi blip
- [ ] Jawaban: "hup!" lalu suara jawaban; efek tidak menimpa suara jawaban
- [ ] Bicara terlalu pelan / server mati: suara bingung / kaget
- [ ] Biarkan 2 menit: menguap, ngorok dua kali, lalu hening; tekan tombol: kaget, menggeliat, melambai
- [ ] Presensi dibuka/tercatat/deadline (dari `/v1/updates`): bunyi masing-masing
- [ ] `SOUND_EFFECTS 0`: hening, kecuali presensi dibuka
- [ ] Animasi UI baru lancar (lihat risiko di atas)
