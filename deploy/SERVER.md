# Deploy ke server (Ubuntu)

## Instalasi

```bash
sudo apt update && sudo apt install -y python3 python3-venv
cd ~/Tugas_Akhir
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt && .venv/bin/pip install -e .
.venv/bin/playwright install --with-deps chromium
cp .env.example .env && chmod 600 .env
```

RAM 2 GB cukup bila ditambah swap 2 GB (Chromium + OCR).

## Login pertama

Server tidak punya layar, jadi login dilakukan di laptop lalu sesinya disalin:

```bash
# laptop
python -m edupad login
python -m edupad schedule --login
scp user_data/session.json user_data/satu_session.json ubuntu@SERVER:Tugas_Akhir/user_data/

# server
chmod 700 user_data && chmod 600 user_data/*.json
.venv/bin/python -m edupad keepalive     # harus: [ok] Sesi aktif
```

## Jadwal

```bash
crontab deploy/crontab
```

## Server perangkat ESP32

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"   # isi EDUPAD_DEVICE_TOKEN di .env
sudo cp deploy/edupad-server.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now edupad-server
curl http://localhost:8000/v1/health                              # harus: {"status": "ok"}
```

Server hanya mendengarkan di `127.0.0.1:8000`; dari internet (perangkat ESP32 dan browser)
lewat Caddy di `https://shata.id` (bagian berikut), jadi port 8000 tetap tertutup. Server
menolak berjalan tanpa `EDUPAD_DEVICE_TOKEN` bila bisa dicapai dari internet (`--host 0.0.0.0`
atau `EDUPAD_PUBLIC_URL` bukan localhost). Kontrak API untuk firmware: [DEVICE_API.md](DEVICE_API.md).

## Login Google & Classroom (web EduPad)

### 1. Google Cloud Console (sekali)

1. Buat project di <https://console.cloud.google.com>, lalu **APIs & Services → Library →
   Google Classroom API → Enable**.
2. **Google Auth Platform → Branding**: nama aplikasi `EduPad`, email dukungan, logo (opsional).
3. **Audience**: user type **External**, status **Testing**, lalu tambahkan email Google yang
   boleh login di **Test users** (maks. 100 selama Testing).
4. **Data Access → Add or remove scopes**, tambahkan (semua hanya-baca):
   `openid`, `.../auth/userinfo.email`, `.../auth/userinfo.profile`,
   `.../auth/classroom.courses.readonly`, `.../auth/classroom.coursework.me.readonly`,
   `.../auth/classroom.courseworkmaterials.readonly`,
   `.../auth/classroom.announcements.readonly`, `.../auth/classroom.topics.readonly`.
5. **Clients → Create client → Web application**. Isi **Authorized redirect URIs**:
   - pengembangan: `http://localhost:5173/auth/google/callback`
   - produksi: `https://<domain>/auth/google/callback`

   *Authorized JavaScript origins* tidak perlu diisi (login berjalan di server).
6. Salin Client ID & Client secret ke `.env` (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`), isi
   `EDUPAD_PUBLIC_URL` dan `EDUPAD_OWNER_EMAILS`. Saat start, `edupad serve` mencetak redirect
   URI yang dipakai; harus sama persis dengan yang didaftarkan.

Batasan dari Google yang perlu diketahui:

- **Status Testing: refresh token berlaku 7 hari.** Setelah itu sinkronisasi gagal
  (`logs/classroom.log`: "perlu login ulang") dan dashboard meminta izin ulang; pengguna cukup
  login lagi. Agar tidak kedaluwarsa dan bisa dipakai siapa pun, aplikasi harus di-*publish*
  dan lolos verifikasi Google untuk scope Classroom (butuh domain, halaman beranda, dan
  kebijakan privasi).
- **Redirect URI produksi wajib HTTPS dengan nama domain**; Google menolak alamat IP
  (mis. `http://16.78.28.191`). Hanya `localhost` yang boleh HTTP.
- Akun Classroom sekolah (Google Workspace for Education) bisa diblokir admin sekolah untuk
  aplikasi pihak ketiga yang belum diverifikasi; akun `@gmail.com` biasa tidak terpengaruh.

### 2. Domain & HTTPS di server (Cloudflare + Caddy)

`shata.id` dikelola Cloudflare dengan proxy aktif (awan oranye): browser dan perangkat
terhubung ke Cloudflare, Cloudflare meneruskan ke VPS lewat HTTPS.

1. **Cloudflare → SSL/TLS → Overview**: mode **Full (strict)**.
2. **Cloudflare → SSL/TLS → Origin Server → Create Certificate**: RSA 2048, hostname
   `shata.id` dan `*.shata.id`, berlaku 15 tahun. Simpan *Origin Certificate* sebagai
   `/etc/caddy/certs/shata.id.pem` dan *Private Key* sebagai `/etc/caddy/certs/shata.id.key`
   di server (`sudo chown root:caddy` dan `chmod 640` untuk kunci).
3. **AWS → EC2 → Security Group**: inbound TCP **443** dari rentang IP Cloudflare
   (<https://www.cloudflare.com/ips/>), atau `0.0.0.0/0` bila ingin sederhana. Port 8000
   tidak perlu dibuka.
4. Caddy:

```bash
sudo apt install -y caddy
sudo cp deploy/Caddyfile /etc/caddy/Caddyfile && sudo systemctl reload caddy
```

`.env` server: `EDUPAD_PUBLIC_URL=https://shata.id` (cookie sesi otomatis bertanda `Secure`).

### 3. Halaman web (React)

Server Ubuntu tidak perlu Node.js: build di laptop (Node 18+), lalu salin hasilnya.

```bash
# laptop
cd web && npm ci && npm run build
ssh ubuntu@SERVER "mkdir -p Tugas_Akhir/web && rm -rf Tugas_Akhir/web/dist"
scp -r dist ubuntu@SERVER:Tugas_Akhir/web/

# server
sudo systemctl restart edupad-server
curl -I https://shata.id/                    # harus: HTTP/2 200
```

### 4. Sinkronisasi

`crontab deploy/crontab` sudah memuat `python -m edupad classroom` tiap 2 jam; satu kali
juga dijalankan otomatis tepat setelah pengguna login. Manual:
`.venv/bin/python -m edupad classroom [--email EMAIL]`.

### 5. Dashboard EduPad (AI Office, Keuangan, Tutor, Equity Radar)

Dashboard (`dashboard/`, buatan tim) disajikan Office API di `https://shata.id/dashboard/`.
Setelah login Google di halaman depan, pengguna langsung dibawa ke sana. Hanya email di
`EDUPAD_OWNER_EMAILS` yang bisa membuka datanya.

Tabel Supabase keuangan & tutor: `supabase/migrations/20261017_finance_tutor.sql`
(sekali, lewat SQL Editor Supabase).

```bash
# laptop: build (dashboard memakai kode game di frontend/, jadi keduanya di-install)
(cd frontend && npm ci) && (cd dashboard && npm ci && npm run build)
rsync -az --delete dashboard/dist/ ubuntu@SERVER:Tugas_Akhir/dashboard/dist/

# server
.venv/bin/pip install -e ".[office]"
sudo cp deploy/edupad-office.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now edupad-office
sudo cp deploy/Caddyfile /etc/caddy/Caddyfile && sudo systemctl reload caddy
curl -I https://shata.id/dashboard/            # harus: HTTP/2 200
curl https://shata.id/v1/dashboard/schedule    # harus: 401 (perlu login)
```

Opsional di `.env`: `EDUPAD_SEMESTER_MEETINGS=16`, `EDUPAD_MIN_ATTENDANCE=0.75` (batas
kehadiran untuk peringatan dini). `EDUPAD_OFFICE_AUTH=off` hanya untuk pengembangan lokal.

## Log

`logs/keepalive.log`, `logs/pipeline.log`, `logs/scrape.log`, `logs/assignments.log`,
`logs/convert.log`, `logs/corpus.log`, `logs/schedule.log`, `logs/serve.log`,
`logs/classroom.log`.

## Keamanan

- `user_data/` dan `.env` berisi rahasia; jangan disalin ke tempat lain.
- Bila server dicurigai bocor: logout dari kelas.usu.ac.id di browser, maka
  cookie di server langsung tidak berlaku.
- `user_data/google/` berisi refresh token Google (akses baca Classroom). Bila bocor: tiap
  pengguna mencabut akses EduPad di <https://myaccount.google.com/permissions>, dan buat ulang
  Client secret di Google Cloud Console.
