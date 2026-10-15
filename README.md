# EduPad Data

Pengumpul dan pengolah data perkuliahan USU untuk AI agent **EduPad**
(asisten belajar berbasis suara di ESP32-S3).

Sistem ini mengambil materi, tugas, dan jadwal kuliah secara otomatis, lalu
menyusunnya menjadi data yang siap dibaca AI agent.

## Alur data

```
kelas.usu.ac.id ──► scrape ───────► data/materials/   (file asli + manifest)
                └─► assignments ──► data/assignments/ (tugas, deadline, status)
satu.usu.ac.id  ──► schedule ─────► data/schedule/    (jadwal kuliah, presensi, KRS)
                └─► attendance ───► data/schedule/attendance.json + notifikasi presensi dibuka

data/materials ──► convert   ──► data/markdown/  (Markdown per file + metadata)
               ──► corpus    ──► data/corpus/    (siap dipakai AI agent)
               ──► summarize ──► data/corpus/summaries.json (ringkasan per pertemuan)
               ──► index     ──► Supabase material_chunks (embedding bge-m3)

pertanyaan ──► ask/chat ──► DeepSeek + tools (search_materials, get_meeting, list_assignments)
                        ──► jawaban suara + layar LCD (+ detail Markdown)
                        ──► memory percakapan & fakta pengguna di Supabase
```

`data/corpus/` berisi:

| File | Isi | Dipakai untuk |
|---|---|---|
| `catalog.json` | Mata kuliah di KRS, alias ("PV", "MSBD"), daftar pertemuan | Mencocokkan nama mata kuliah |
| `meetings/<course_id>/pNN.md` | Seluruh materi satu pertemuan | Pertanyaan "pertemuan 5 PV tentang apa" |
| `chunks.jsonl` | Potongan ~350 kata + metadata & lokasi sumber | Embedding / vector database |
| `summaries.json` | Ringkasan & daftar topik per pertemuan (dibuat ulang hanya bila materi berubah) | Jawaban hemat token untuk `get_meeting` |

## Struktur proyek

```
src/edupad/
├── config.py          path, URL, pengaturan .env
├── cli.py             pintu masuk: python -m edupad <perintah>
├── core/              sesi, klien Moodle & Supabase, koneksi HTTP bersama, file, logging, notifikasi
├── collectors/        materials (Playwright), assignments, schedule
├── processing/        convert (PDF/PPTX/DOCX -> Markdown), corpus, summaries, embeddings, index
├── agent/             assistant (loop LLM), tools, memory, formatting, evaluate
├── voice/             stt (Groq Whisper), tts (ElevenLabs); PCM 16 kHz untuk ESP32
├── server.py          HTTP API perangkat ESP32 (deploy/DEVICE_API.md)
└── jobs/              keepalive, pipeline
tests/                 unit test (pytest)
evals/                 set uji AI agent & hasil evaluasi
deploy/                crontab, panduan server, jadwal Windows
data/  logs/  user_data/   dibuat saat berjalan (tidak dibagikan)
```

## EduPad AI Office

Dashboard utama berada di `dashboard/` dan memakai React, TypeScript, Vite, Recharts,
serta Phaser 3. Halaman pertama adalah kantor virtual 2D; halaman presensi, tugas,
jadwal, percakapan, riwayat belajar, dan monitoring memakai gaya dashboard yang sama.
Implementasi Office lama di `frontend/` tetap dipertahankan sebagai sumber komponen game
dan preview mandiri. Office API adalah adapter terpisah di `src/edupad/office/`; API
perangkat ESP32 `/v1/*` tidak berubah.

```bash
pip install -e ".[dev,office]"
python -m edupad office-api --host 127.0.0.1 --port 8001

# terminal worker (mengeksekusi task Office yang diizinkan)
python -m edupad office-worker

# terminal lain (dashboard terpadu)
cd dashboard
npm install
npm run dev
```

Dashboard memakai `/api/office/snapshot`, `/api/office/events` (SSE), dan endpoint baca-saja
`/v1/dashboard/*`. Data dashboard berasal dari file `data/`, log lokal, serta tabel Supabase
yang sudah dipakai EduPad; mode dummy hanya aktif jika `VITE_DATA_SOURCE=mock` ditetapkan
secara eksplisit. Bila migration
`supabase/migrations/20261013_edu_pad_office.sql` belum diterapkan, penyimpanan tugas dan event
otomatis memakai `data/office/` secara lokal. Migration hanya file sumber dan tidak dijalankan
otomatis. Setelah migration diterapkan, set `EDUPAD_OFFICE_STORAGE=supabase` untuk mengaktifkan
sinkronisasi Supabase; mode default tetap `local` agar backend lama tidak terganggu.
Vertical slice worker saat ini sengaja hanya menerima job `index` dan hanya melakukan claim pada
storage lokal. Worker menolak mode Supabase sampai migration claiming atomik ditinjau dan
disetujui; tidak ada migration yang dijalankan otomatis.

## Instalasi

Python 3.10+.

```bash
pip install -e ".[dev]"        # atau: pip install -r requirements.txt && pip install -e .
playwright install chromium
cp .env.example .env           # isi token Telegram (opsional)
```

## Perintah

| Perintah | Fungsi |
|---|---|
| `python -m edupad login` | Login SSO kelas.usu.ac.id di browser, simpan sesi |
| `python -m edupad scrape [--course ID ...] [--list] [--headless]` | Unduh materi |
| `python -m edupad assignments [--course ID ...]` | Tugas & kuis: deadline, status, soal |
| `python -m edupad schedule [--login]` | Jadwal kuliah & presensi dari portal SATU |
| `python -m edupad attendance [--fill] [--dry-run]` | Cek presensi yang dibuka, notifikasi Telegram; `--fill` mengisi presensi mandiri |
| `python -m edupad convert [--force]` | Konversi materi ke Markdown |
| `python -m edupad corpus` | Bersihkan & potong materi untuk AI agent |
| `python -m edupad summarize [--force]` | Ringkasan per pertemuan (DeepSeek) |
| `python -m edupad index [--force]` | Embed chunk & sinkronkan ke Supabase |
| `python -m edupad ask "..." [--detail] [--trace] [--new] [--no-memory] [--speak]` | Tanya AI agent; percakapan diingat per sesi; `--speak` menyuarakan jawaban |
| `python -m edupad ask --audio rekaman.wav [opsi yang sama]` | Tanya lewat rekaman suara (STT -> agent); dengan `--speak` alurnya suara-ke-suara |
| `python -m edupad transcribe rekaman.wav` | Ubah rekaman jadi teks saja (uji STT) |
| `python -m edupad serve [--host 0.0.0.0] [--port 8000]` | Server HTTP untuk perangkat ESP32: rekaman -> STT -> agent -> layar + audio ([API](deploy/DEVICE_API.md)) |
| `python -m edupad chat [--detail] [--trace] [--new] [--speak]` | Percakapan berlanjut |
| `python -m edupad memory [--clear]` | Lihat / hapus memory AI agent |
| `python -m edupad eval --label X [--repeat N] [--detail] [--no-memory]` | Ukur token, biaya & kualitas agent pada set uji (default: konfigurasi produksi) |
| `python -m edupad keepalive` | Perpanjang sesi kelas.usu.ac.id & portal SATU |
| `python -m edupad pipeline` | scrape → assignments → convert → corpus → summarize → index |

Kode keluar: `0` sukses, `1` error, `2` sesi habis (perlu login manual).

## Suara (STT & TTS)

`voice/stt.py`: `transcribe_pcm(pcm)` mengubah rekaman mikrofon ESP32-S3 (PCM 16-bit mono
16 kHz) menjadi teks; `transcribe(bytes, nama_file)` untuk file wav/mp3/m4a/ogg/flac/webm.
Penyedia: Groq, model `whisper-large-v3-turbo`, bahasa Indonesia, dengan nama & singkatan
mata kuliah dari `catalog.json` sebagai prompt ejaan. Rekaman tanpa ucapan (hening/derau,
< -35 dBFS) tidak dikirim, karena Whisper mengubahnya menjadi "Terima kasih.". Uji:
~0,5–1 detik per pertanyaan. Coba dengan `python -m edupad transcribe rekaman.wav`.

`voice/tts.py`: `stream(teks)` menghasilkan potongan PCM 16-bit mono 16 kHz (format ESP32-S3)
begitu tersedia; `synthesize()` mengembalikan audio utuh. Penyedia: ElevenLabs, suara buatan
sendiri "EduPad" (Voice Design), model `eleven_multilingual_v2`. Jawaban panjang dipecah: kalimat
pertama & sisanya disintesis bersamaan dengan konteks `previous_text`/`next_text` (tidak ditagih,
intonasi tetap menyambung), maks. 2 permintaan paralel (batas akun gratis). Uji: audio pertama
~0,95 detik (sebelumnya 2,2–2,5 detik untuk jawaban ~330 karakter).
Akun gratis: 10.000 karakter/bulan (~30 jawaban) dan hanya suara bawaan / buatan sendiri.

## Sesi login

- **kelas.usu.ac.id**: batas sesi 8 jam tanpa aktivitas. `keepalive` tiap 20 menit
  menjaganya tetap aktif. Sesi tidak terikat IP, jadi bisa login di laptop lalu
  menyalin `user_data/session.json` ke server.
- **Portal SATU** (jadwal): sesi Keycloak berakhir setelah beberapa jam tidak
  dipakai. Jadwal jarang berubah, jadi data terakhir tetap dipakai; login ulang
  (`schedule --login`) cukup saat KRS berubah.

Bila sesi habis, notifikasi Telegram dikirim sekali.

## AI agent

- **Pencarian**: hybrid (vektor bge-m3 + kata kunci) mengambil 20 kandidat, lalu diurutkan ulang
  dengan reranker `bge-reranker-base` (fusi peringkat); 4 potongan teratas dikirim ke LLM.
- **Hemat token**: potongan yang sudah dikirim tidak dikirim ulang; `get_meeting` mengirim
  ringkasan kecuali diminta `full=true`. Default **mode perangkat**: hanya suara + layar LCD;
  jawaban Markdown panjang hanya dengan `--detail` / `ask(..., with_detail=True)`.
  Pemakaian token & biaya per pertanyaan dicatat di `logs/agent_usage.jsonl`. Batas keluaran
  dan putaran tool dikendalikan oleh `EDUPAD_LLM_MAX_OUTPUT_TOKENS` dan
  `EDUPAD_LLM_MAX_TOOL_ROUNDS`; frontend preview tidak memanggil DeepSeek.
- **Memory**: percakapan disimpan per sesi (sesi baru setelah 30 menit menganggur) di Supabase
  (`agent_sessions`, `agent_turns`); 8 giliran lama diringkas otomatis. Fakta tentang pengguna
  (`agent_memories`) dipakai lintas sesi. `memory --clear` menghapus semuanya.
- **Evaluasi**: `evals/agent_cases.json` (20 kasus, termasuk pertanyaan lanjutan dan materi
  yang tidak ada). Jawaban dinilai dengan cek sumber, kata kunci, dan LLM-as-judge
  (`deepseek-flash`) terhadap materi asli. Hasil di `evals/results/`. Mode perangkat vs agent
  awal: biaya per jawaban −47%, waktu jawab −22%, ketepatan sama (4,96/5), tanpa halusinasi.

## Prinsip

- **Moodle hanya dibaca.** Tidak pernah mengirim, mengumpulkan, atau mengubah data di Moodle.
  Satu-satunya penulisan ke layanan kampus adalah `attendance --fill` (presensi mandiri SATU).
- **Tidak menyimpan password.** Yang disimpan hanya cookie sesi di `user_data/`.
- **Konversi lokal.** Konversi & OCR berjalan di mesin sendiri. Teks materi dikirim ke
  Cloudflare Workers AI (embedding, reranker) dan DeepSeek (ringkasan, jawaban) untuk AI agent.
  Rekaman pertanyaan dikirim ke Groq (STT) dan teks jawaban suara ke ElevenLabs (TTS); rekaman
  hening disaring di server dan tidak dikirim.
- **Sopan ke server.** Jeda 2,5 detik antar request; unduhan inkremental.

## Pengujian

```bash
python -m pytest                       # unit test, tanpa jaringan & tanpa memakai kuota API
python -m ruff check src tests         # lint
python -m ruff format src tests        # format (lebar baris 100, lihat pyproject.toml)
```

Test memakai tiruan untuk semua layanan luar (DeepSeek, Groq, ElevenLabs, Supabase); tiruan
bersama ada di `tests/fakes.py`. Jalankan ketiga perintah di atas sebelum commit.

## Deploy

Lihat [deploy/SERVER.md](deploy/SERVER.md); kontrak API perangkat ESP32 di
[deploy/DEVICE_API.md](deploy/DEVICE_API.md).
