# EduPad Data

Pengumpul dan pengolah data perkuliahan untuk AI agent **EduPad**
(asisten belajar berbasis suara di ESP32-S3).

Sistem ini mengambil materi, tugas, dan jadwal kuliah secara otomatis dari e-learning USU
(kelas.usu.ac.id, portal SATU) dan dari Google Classroom (untuk umum, login lewat web
EduPad), lalu menyusunnya menjadi data yang siap dibaca AI agent.

## Alur data

```
kelas.usu.ac.id ──► scrape ───────► data/materials/   (file asli + manifest)
                └─► assignments ──► data/assignments/ (tugas, deadline, status)
satu.usu.ac.id  ──► schedule ─────► data/schedule/    (jadwal kuliah, presensi, KRS)
                └─► attendance ───► data/schedule/attendance.json + notifikasi presensi dibuka
Google Classroom ─► classroom ────► data/classroom/   (kelas, tugas + status, materi, pengumuman)

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
├── agent/             assistant (loop LLM), tools, memory, formatting, evaluate,
│                      finance (keuangan suara), tutor (kuis lisan), radar (Equity Radar)
├── office/            Office API dashboard: login Google pemilik, data panel, event owl
├── voice/             stt (Groq Whisper), tts (ElevenLabs), mode (Mode Suara), clips (pesan status
│                      bersuara); PCM 16 kHz untuk ESP32
├── google/            oauth (login Google + PKCE), accounts (refresh token & sesi web)
├── server.py          HTTP API perangkat ESP32 (deploy/DEVICE_API.md) + web
├── device_status.py   status perangkat terakhir (RSSI, uptime, firmware) untuk dashboard
├── webapp.py          web: login Google, /api, halaman React hasil build
└── jobs/              keepalive, pipeline
web/                   halaman web React + Tailwind (halaman depan & login Google)
dashboard/             dashboard EduPad (AI Office, keuangan, Tutor, Equity Radar, monitoring)
frontend/              kantor virtual Phaser (kode game dipakai dashboard; preview mandiri)
firmware/              sketch ESP32-S3 (LCD, mic, speaker) + pratinjau layar di PC
supabase/migrations/   tabel tambahan (keuangan, tutor, Office)
tests/                 unit test (pytest)
evals/                 set uji AI agent & hasil evaluasi
deploy/                crontab, panduan server, jadwal Windows
data/  logs/  user_data/   dibuat saat berjalan (tidak dibagikan)
```

## Dashboard EduPad (AI Office)

Dashboard di `dashboard/` (React, TypeScript, Vite, Recharts, Phaser 3) disajikan di
`https://shata.id/dashboard/`. Setelah login Google di halaman depan (`web/`), pemilik
(`EDUPAD_OWNER_EMAILS`) langsung dibawa ke sini. Halaman pertama adalah kantor virtual 2D:
tujuh owl bergerak sesuai pekerjaan AI agent yang sebenarnya, termasuk saat perangkat ESP32
ditanya (SORA tutor, KOIN keuangan, TEMPO jadwal, NEXUS pengetahuan). Kode game ada di
`frontend/src/game` (juga bisa dijalankan mandiri sebagai preview).

Fitur yang tersambung dengan perangkat (satu sumber data untuk suara & dashboard):

| Fitur | Lewat suara di perangkat | Di dashboard |
|---|---|---|
| Keuangan | "tadi beli makan dua puluh lima ribu", "sisa anggaran makanku?", "atur anggaran transportasi tiga ratus ribu", "hapus yang tadi" | `#/keuangan`: catat manual, anggaran, laporan; transaksi suara diberi label |
| Tutor Belajar (SDG 4.1/4.4) | "uji aku Basis Data pertemuan dua", "aku belum paham rekursi", "hari ini belajar apa?", "mulai" (bantuan SORA) | `#/tutor`: bantuan SORA (sebelum/sesudah), kurva belajar, penguasaan per topik, salah paham |
| Equity Radar (SDG 4.5/4.a/10) | peringatan dini & pengingat mengulang tampil sebagai kartu di layar | `#/equity`: kesenjangan akses materi, kehadiran vs syarat ujian, langkah berikutnya |
| Mode Suara (SDG 4.5, mahasiswa tunanetra) | "aktifkan mode suara", "bicara lebih cepat", "lanjut": semua jawaban & pemberitahuan dibacakan, bunyi penanda, pesan status tersimpan di perangkat | `#/pengaturan`: nyalakan & kecepatan; `#/equity`: kartu Aksesibilitas (pertemuan yang bisa didengar, halaman OCR, suara yang diputar) |
| Monitoring | status perangkat dikirim lewat header (RSSI, uptime, firmware) | `#/monitoring`: perangkat, latensi `/v1/ask`, error |

- Office API (`src/edupad/office/`, `python -m edupad office-api`, port 8001) melayani
  `/dashboard/`, `/api/office/*`, dan `/v1/dashboard/*`; semuanya memerlukan sesi login Google
  pemilik dari web EduPad (`EDUPAD_OFFICE_AUTH=off` hanya untuk pengembangan lokal).
- Keuangan & Tutor disimpan di Supabase: jalankan `supabase/migrations/20261017_finance_tutor.sql`
  dan `20261018_tutor_help.sql` sekali. Logika ada di `src/edupad/agent/finance.py`, `tutor.py`,
  `coach.py`, dan `radar.py` (tool agent + data dashboard).
- **Tutor mandiri (SORA)**: `python -m edupad tutor-coach` (cron 15:30 WIB) mencari topik dengan
  minimal dua tanda kesulitan (jawaban kuis salah, penguasaan rendah, pengulangan terlewat,
  pertanyaan berulang, ucapan "belum paham"; kehadiran tidak dipakai), mencatatnya sebagai
  ingatan agent, lalu menyiapkan pelajaran mini 3 bagian + kuis terarah. Bantuan ditawarkan lewat
  kartu sore di perangkat dan saat mahasiswa bicara ke EduPad; skor sebelum/sesudah tampil di
  dashboard. Soal kuis per pertemuan disimpan di `data/tutor/bank.json` (kuis berikutnya
  langsung mulai; tingkat soal mengikuti penguasaan).
- Status owl dikirim dari antrean latar belakang, sehingga jawaban perangkat tidak menunggu.
  Penyimpanan event/tugas Office default lokal (`data/office/`); tabel Office di
  `supabase/migrations/20261013_edu_pad_office.sql` opsional (`EDUPAD_OFFICE_STORAGE=supabase`).

```bash
pip install -e ".[dev,office]"
python -m edupad serve                    # web + login Google + API perangkat (port 8000)
python -m edupad office-api               # dashboard API (port 8001)
cd web && npm run dev                     # http://localhost:5173 (login)
cd frontend && npm ci && cd ../dashboard && npm ci && npm run dev   # http://localhost:5174/dashboard/
```

Deploy: `deploy/SERVER.md` bagian "Dashboard EduPad".

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
| `python -m edupad assignments [--course ID ...]` | Tugas & kuis: deadline, status, soal (cron tiap 15 menit: status pengumpulan dipakai pengingat deadline) |
| `python -m edupad schedule [--login]` | Jadwal kuliah & presensi dari portal SATU |
| `python -m edupad attendance [--fill] [--dry-run]` | Cek presensi yang dibuka, notifikasi Telegram; `--fill` mengisi presensi mandiri |
| `python -m edupad classroom [--email EMAIL]` | Kelas, tugas + status, materi & pengumuman Google Classroom akun yang login di web |
| `python -m edupad convert [--force]` | Konversi materi ke Markdown |
| `python -m edupad corpus` | Bersihkan & potong materi untuk AI agent |
| `python -m edupad summarize [--force]` | Ringkasan per pertemuan (DeepSeek) |
| `python -m edupad index [--force]` | Embed chunk & sinkronkan ke Supabase |
| `python -m edupad ask "..." [--detail] [--trace] [--new] [--no-memory] [--speak]` | Tanya AI agent; percakapan diingat per sesi; `--speak` menyuarakan jawaban |
| `python -m edupad ask --audio rekaman.wav [opsi yang sama]` | Tanya lewat rekaman suara (STT -> agent); dengan `--speak` alurnya suara-ke-suara |
| `python -m edupad transcribe rekaman.wav` | Ubah rekaman jadi teks saja (uji STT) |
| `python -m edupad serve [--host 0.0.0.0] [--port 8000]` | Server HTTP: perangkat ESP32 (rekaman -> STT -> agent -> layar + audio, [API](deploy/DEVICE_API.md)) dan web EduPad (login Google) |
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
- **Portal SATU** (jadwal & presensi): sesi portal punya batas ~8 jam, tetapi cookie SSO
  Keycloak ("Ingat saya" saat login) berlaku ~30 hari. `keepalive`, presensi, dan jadwal
  membuat sesi portal baru lewat cookie itu tanpa password, jadi login ulang
  (`schedule --login`, lalu salin `user_data/satu_session.json` ke server) hanya perlu
  bila cookie SSO-nya sendiri habis.

Bila sesi habis, notifikasi Telegram dikirim sekali.

## AI agent

- **Pencarian**: hybrid (vektor bge-m3 + kata kunci) mengambil 20 kandidat, lalu diurutkan ulang
  dengan reranker `bge-reranker-base` (fusi peringkat); 4 potongan teratas dikirim ke LLM.
- **Hemat token**: potongan yang sudah dikirim tidak dikirim ulang; `get_meeting` mengirim
  ringkasan kecuali diminta `full=true`. Default **mode perangkat**: hanya suara + layar LCD;
  jawaban Markdown panjang hanya dengan `--detail` / `ask(..., with_detail=True)`.
  Pemakaian token & biaya per pertanyaan dicatat di `logs/agent_usage.jsonl`. Batas opsional:
  `EDUPAD_LLM_MAX_OUTPUT_TOKENS` dan `EDUPAD_LLM_MAX_TOOL_ROUNDS` (default 5 putaran).
- **Memory**: percakapan disimpan per sesi (sesi baru setelah 30 menit menganggur) di Supabase
  (`agent_sessions`, `agent_turns`); 8 giliran lama diringkas otomatis. Fakta tentang pengguna
  (`agent_memories`) dipakai lintas sesi. `memory --clear` menghapus semuanya.
- **Evaluasi**: `evals/agent_cases.json` (20 kasus, termasuk pertanyaan lanjutan dan materi
  yang tidak ada). Jawaban dinilai dengan cek sumber, kata kunci, dan LLM-as-judge
  (`deepseek-flash`) terhadap materi asli. Hasil di `evals/results/`. Mode perangkat vs agent
  awal: biaya per jawaban −47%, waktu jawab −22%, ketepatan sama (4,96/5), tanpa halusinasi.

## Prinsip

- **Moodle hanya dibaca.** Tidak pernah mengirim, mengumpulkan, atau mengubah data di Moodle.
  Satu-satunya penulisan ke layanan kampus adalah `attendance --fill` (presensi mandiri SATU),
  lewat cron atau saat mahasiswa sendiri memintanya ke EduPad (tool `fill_attendance`).
- **Tidak menyimpan password.** Yang disimpan hanya cookie sesi di `user_data/`.
- **Konversi lokal.** Konversi & OCR berjalan di mesin sendiri. Teks materi dikirim ke
  Cloudflare Workers AI (embedding, reranker) dan DeepSeek (ringkasan, jawaban) untuk AI agent.
  Rekaman pertanyaan dikirim ke Groq (STT) dan teks jawaban suara ke ElevenLabs (TTS); rekaman
  hening disaring di server dan tidak dikirim.
- **Sopan ke server.** Jeda 2,5 detik antar request; unduhan inkremental.

## Web & Google Classroom

Halaman depan (`/`) hanya berisi EduPad dan tombol **Masuk dengan Google**. Login berhasil
langsung ke `/dashboard`. Login memakai OAuth authorization code + PKCE di server
(`google/oauth.py`), dengan izin baca-saja Classroom dan `access_type=offline`. Refresh token
disimpan di `user_data/google/` (0600) sehingga `python -m edupad classroom` (cron tiap 2 jam,
dan sekali tepat setelah login) bisa mengambil data tanpa pengguna hadir.

Data Classroom masuk ke agent dengan bentuk yang sama seperti e-learning USU:

- **Tugas & deadline** ikut di `list_assignments` (bertanda `"sumber": "Google Classroom"`),
  lengkap dengan status pengumpulan ("BELUM dikumpulkan — LEWAT DEADLINE", nilai, dst.).
- **Materi & pengumuman** lewat tool `get_classroom_materials` (filter kelas, kata kunci,
  pertemuan), dan kelasnya tercantum di system prompt. Tool ini hanya ditawarkan ke LLM bila
  pengguna punya data Classroom, jadi pengguna USU saja tidak membayar token tambahan.
- Agent di perangkat/CLI membaca Classroom milik email di `EDUPAD_OWNER_EMAILS`; akun Google
  lain mendapat ruang data sendiri (`user_id` = `google-<id>`).

Pengembangan (dua terminal):

```bash
python -m edupad serve                       # backend + login Google di :8000
cd web && npm install && npm run dev         # halaman di http://localhost:5173
```

Pengaturan Google Cloud Console, domain HTTPS, dan deploy: [deploy/SERVER.md](deploy/SERVER.md).

## Pengujian

```bash
python -m pytest                       # unit test, tanpa jaringan & tanpa memakai kuota API
python -m ruff check src tests         # lint
python -m ruff format src tests        # format (lebar baris 100, lihat pyproject.toml)
cd web && npm run build                # cek tipe TypeScript + build halaman web
```

Test memakai tiruan untuk semua layanan luar (DeepSeek, Groq, ElevenLabs, Supabase, Google);
tiruan bersama ada di `tests/fakes.py`. Jalankan perintah di atas sebelum commit.

## Deploy

Lihat [deploy/SERVER.md](deploy/SERVER.md); kontrak API perangkat ESP32 di
[deploy/DEVICE_API.md](deploy/DEVICE_API.md).
