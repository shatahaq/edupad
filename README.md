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
├── core/              sesi, klien Moodle, file, logging, notifikasi
├── collectors/        materials (Playwright), assignments, schedule
├── processing/        convert (PDF/PPTX/DOCX -> Markdown), corpus, summaries, embeddings, index
├── agent/             assistant (loop LLM), tools, memory, formatting, evaluate
├── voice/             tts (ElevenLabs, PCM 16 kHz untuk ESP32)
└── jobs/              keepalive, pipeline
tests/                 unit test (pytest)
evals/                 set uji AI agent & hasil evaluasi
deploy/                crontab, panduan server, jadwal Windows
data/  logs/  user_data/   dibuat saat berjalan (tidak dibagikan)
```

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
| `python -m edupad chat [--detail] [--trace] [--new] [--speak]` | Percakapan berlanjut |
| `python -m edupad memory [--clear]` | Lihat / hapus memory AI agent |
| `python -m edupad eval --label X [--repeat N] [--detail] [--no-memory]` | Ukur token, biaya & kualitas agent pada set uji (default: konfigurasi produksi) |
| `python -m edupad keepalive` | Perpanjang sesi kelas.usu.ac.id & portal SATU |
| `python -m edupad pipeline` | scrape → assignments → convert → corpus → summarize → index |

Kode keluar: `0` sukses, `1` error, `2` sesi habis (perlu login manual).

## Suara (TTS)

`voice/tts.py`: `stream(teks)` menghasilkan potongan PCM 16-bit mono 16 kHz (format ESP32-S3)
begitu tersedia; `synthesize()` mengembalikan audio utuh. Penyedia: ElevenLabs, suara buatan
sendiri "EduPad" (Voice Design), model `eleven_multilingual_v2`. Uji: audio pertama ~1–2 detik.
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
  Pemakaian token & biaya per pertanyaan dicatat di `logs/agent_usage.jsonl`.
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
- **Sopan ke server.** Jeda 2,5 detik antar request; unduhan inkremental.

## Pengujian

```bash
python -m pytest
python -m ruff check src tests
```

## Deploy

Lihat [deploy/SERVER.md](deploy/SERVER.md).
