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

Buka port 8000 (TCP) di firewall/security group VPS. Server menolak berjalan di `0.0.0.0`
tanpa `EDUPAD_DEVICE_TOKEN`. Koneksi masih HTTP biasa, jadi token terlihat di jaringan; untuk
pemakaian di luar uji coba, pasang HTTPS lewat reverse proxy (mis. Caddy). Kontrak API untuk
firmware: [DEVICE_API.md](DEVICE_API.md).

## Log

`logs/keepalive.log`, `logs/pipeline.log`, `logs/scrape.log`, `logs/assignments.log`,
`logs/convert.log`, `logs/corpus.log`, `logs/schedule.log`, `logs/serve.log`.

## Keamanan

- `user_data/` dan `.env` berisi rahasia; jangan disalin ke tempat lain.
- Bila server dicurigai bocor: logout dari kelas.usu.ac.id di browser, maka
  cookie di server langsung tidak berlaku.
