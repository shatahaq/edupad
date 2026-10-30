# EduPad Dashboard

Dashboard terpadu EduPad: kantor virtual AI, hal yang biasa ditanyakan ke perangkat (presensi yang sedang
dibuka, tugas & deadline, jadwal), riwayat percakapan dengan AI agent, dan riwayat belajar.
Monitoring perangkat ESP32, server, dan AI agent ada di tab terpisah (Sistem → Monitoring).
React + TypeScript + Recharts (Vite).

| Halaman | Route | Isi |
|---|---|---|
| AI Office | `#/` | Kantor Phaser dengan tujuh owl, detail pekerja/ruangan/furnitur, editor furnitur lokal, dan status backend |
| Beranda | `#/beranda` | Presensi dibuka sekarang, jadwal hari ini, tugas mendekati deadline, percakapan terakhir |
| Presensi | `#/presensi` | Hari ini + 7 hari ke depan (jendela buka/tutup, cara), rekap kehadiran per matkul |
| Tugas | `#/tugas` | Filter belum dikumpulkan / lewat deadline / selesai; cuplikan soal + tautan Moodle |
| Jadwal | `#/jadwal` | Jadwal mingguan, hari ini disorot |
| Keuangan | `#/keuangan` | Pengelolaan catatan keuangan mahasiswa |
| Riwayat percakapan | `#/percakapan` | Sesi & transkrip: pertanyaan, jawaban suara, layar LCD, sumber materi |
| Riwayat belajar | `#/belajar` | Aktivitas harian, mata kuliah & materi yang dibahas, fakta yang diingat agent |
| Monitoring | `#/monitoring[/<panel>]` | 9 panel kesehatan sistem; `/<panel>` scroll ke kartunya (mis. `#/monitoring/devices`) |

Office dan Keuangan memiliki aksi khusus. Data tugas Office tetap melalui Office API; susunan
furnitur hanya tersimpan di browser, tidak mengubah database atau backend.

```bash
cd apps/dashboard
npm install
npm run dev          # http://127.0.0.1:5173, data backend asli
npm run build        # hasil di dist/ (file statis)
```

## Sumber data: live vs preview dummy

Semua angka lewat satu pintu, [`src/api/client.ts`](src/api/client.ts):

```
komponen panel ──► usePanel("api") ──► fetchPanel("api")
                                          ├─ live: GET {VITE_API_URL}/v1/dashboard/api (default)
                                          └─ mock: src/api/mock/ (hanya VITE_DATA_SOURCE=mock)
```

- Mode default adalah **live** melalui Office API port 8001. Data dummy hanya aktif jika
  `VITE_DATA_SOURCE=mock` dipilih secara eksplisit.
- **Data dummy hanya ada di `src/api/mock/`.** Komponen tidak pernah mengimpornya, dan build
  live (`npm run build:live`) tidak membawanya sama sekali (dimuat lewat import dinamis).
- Sidebar menampilkan label **Data dummy** selama mode mock, supaya tidak tertukar dengan angka asli.
- Bentuk data ditetapkan di [`src/api/types.ts`](src/api/types.ts). Data dummy dicek TypeScript
  terhadap tipe yang sama (`satisfies DashboardData`), jadi kalau tipe berubah, dummy ikut wajib
  diperbarui dan tidak bisa diam-diam berbeda dari server.
- Tiap panel memuat datanya sendiri. Bila satu endpoint gagal, hanya panel itu yang menampilkan
  error (data terakhir tetap terlihat); panel lain tidak terpengaruh.
- Field yang belum bisa diukur (mis. baterai, sinyal Wi-Fi) bertipe `| null` dan tampil "—".

## Menyambungkan ke server

1. Jalankan `python -m edupad office-api --host 127.0.0.1 --port 8001`.
2. Jalankan `npm run dev`. Proxy Vite meneruskan `/api` dan `/v1/dashboard` ke Office API.
3. Untuk deployment beda origin, isi `VITE_API_URL` dengan URL backend. Jangan menaruh
   service-role Supabase atau secret API lain di variabel `VITE_*`.

Server perlu mengizinkan CORS dari asal dashboard, atau sajikan `dist/` dari domain yang sama.

### Sumber data yang sudah ada di server

| Panel | Endpoint | Sumber |
|---|---|---|
| Kesehatan API | `/v1/dashboard/api` | `status` & `timing` tiap POST /v1/ask (perlu dicatat ke log JSONL) |
| AI Agent | `/v1/dashboard/agent` | `logs/agent_usage.jsonl` (tools, detik, token), `evals/results/*.json` |
| Biaya | `/v1/dashboard/cost` | `cost_usd` di `logs/agent_usage.jsonl` |
| Aktivitas | `/v1/dashboard/activity` | Supabase `agent_turns` (waktu & pertanyaan) |
| Basis pengetahuan | `/v1/dashboard/knowledge` | `data/corpus/`, Supabase `material_chunks`, log pipeline |
| Server | `/v1/dashboard/resources` | `psutil` |
| Layanan luar | `/v1/dashboard/services` | latensi/error panggilan Groq, DeepSeek, ElevenLabs, dll. (perlu dicatat) |
| Error | `/v1/dashboard/errors` | `logs/serve.log` / log JSONL yang sama dengan Kesehatan API |
| Perangkat | `/v1/dashboard/devices` | **belum ada**: firmware perlu mengirim ID perangkat (header), baterai, RSSI |

Halaman mahasiswa (belum ada endpoint; semua sumber sudah ada di server):

| Panel | Endpoint | Sumber |
|---|---|---|
| Presensi | `/v1/dashboard/attendance` | `data/schedule/attendance.json`; `window` dihitung dengan `presence_window()` di `agent/tools.py`, `stale` = `STALE_AFTER` |
| Tugas | `/v1/dashboard/assignments` | `data/assignments/assignments.json` (`matkul` dipecah jadi `course` + `kode`, `soal` = `deskripsi[:600]`) |
| Jadwal | `/v1/dashboard/schedule` | `data/schedule/schedule.json` → `kelas[]` |
| Percakapan | `/v1/dashboard/conversations` | Supabase `agent_sessions` + `agent_turns` (question, speech, screen, sources); `tools`/`latency_s` dari `usage` atau log |
| Riwayat belajar | `/v1/dashboard/learning` | Agregasi `agent_turns` (per hari, per matkul dari `sources`) + `agent_memories` |

## Struktur

```
src/
├── api/
│   ├── types.ts      kontrak data (satu tipe per panel)
│   ├── client.ts     pilih mock / live, daftar endpoint
│   ├── usePanel.ts   store bersama per panel: satu fetch + refresh berkala, reloadAll()
│   └── mock/         DATA DUMMY (satu-satunya tempat); student.ts = data halaman mahasiswa
├── components/       Panel/Stat/Meter, PageHeader, Sidebar, Topbar, Kpi, ChartTooltip, Icon
├── pages/            satu file per halaman (Beranda, Presensi, …, Monitoring)
├── panels/           kartu: 9 panel monitoring + panel mahasiswa (presensi, tugas, jadwal, …)
├── lib/              format angka/waktu, gaya chart, menu (nav.ts), routing hash (router.ts)
└── styles.css        token warna & tipografi (tema terang, Geist / Geist Mono)
```
