# Firmware EduPad (ESP32-S3)

Tahan tombol **BOOT**, bicara, lalu lepas: rekaman dikirim ke `POST /v1/ask` sambil merekam,
jawaban (`screen`) tampil di LCD, lalu suaranya (`audio_url`) diputar lewat speaker begitu tiba.
API-nya ada di [../deploy/DEVICE_API.md](../deploy/DEVICE_API.md).

| Tombol BOOT | Fungsi |
|---|---|
| Tahan | Bicara (lepas untuk mengirim) |
| Tekan 1x | Putar ulang suara jawaban terakhir. Server memakai suara yang tersimpan, jadi tidak memakai kuota ElevenLabs |
| Tekan 2x cepat | Mulai percakapan baru (`?new=1`) |
| Tekan saat suara diputar | Hentikan suara (tahan terus untuk langsung bertanya lagi) |

Server hanya menyimpan suara **jawaban terakhir**; jawaban baru menimpanya.

Perangkat keras: ESP32-S3 DevKitC N16R8, LCD SPI ST7796 4" 320x480, mikrofon I2S INMP441,
amplifier I2S MAX98357A + speaker 4-8 ohm.

## Sambungan kabel

LCD ST7796 (pin touch `T_*` dibiarkan lepas):

| LCD | ESP32-S3 |
|---|---|
| VCC | 3V3 (5V bila modul punya regulator 3,3 V) |
| GND | GND |
| CS | GPIO 10 |
| RESET | GPIO 13 |
| DC/RS | GPIO 9 |
| SDI (MOSI) | GPIO 11 |
| SCK | GPIO 12 |
| LED | GPIO 21 (atau langsung 3V3, lalu `PIN_TFT_BL -1`) |
| SDO (MISO) | tidak disambung |

Mikrofon INMP441:

| INMP441 | ESP32-S3 |
|---|---|
| VDD | 3V3 (**bukan** 5V) |
| GND | GND |
| L/R | GND (kanal kiri) |
| SCK | GPIO 4 |
| WS | GPIO 5 |
| SD | GPIO 6 |

Amplifier MAX98357A (sama dengan [speaker_test](speaker_test/speaker_test.ino)):

| MAX98357A | ESP32-S3 |
|---|---|
| VIN | 5V (lebih keras) atau 3V3 |
| GND | GND |
| BCLK | GPIO 15 |
| LRC | GPIO 16 |
| DIN | GPIO 17 |
| GAIN, SD | tidak disambung |
| + / - | speaker (jangan ke GND) |

Volume: `SPEAKER_VOLUME` di `config.h` (0.0-1.0).

Semua pin bisa diubah di [edupad/config.h](edupad/config.h).

## Flash dari Arduino IDE

1. **Board ESP32**: File -> Preferences -> Additional boards manager URLs, isi
   `https://espressif.github.io/arduino-esp32/package_esp32_index.json`, lalu Boards Manager ->
   pasang **esp32** (Espressif Systems).
2. **Library** (Library Manager): **LovyanGFX** (lovyan03) dan **ArduinoJson** (Benoit Blanchon, v7).
3. `edupad/secrets.h` berisi Wi-Fi bawaan dan `EDUPAD_DEVICE_TOKEN` (harus sama dengan `.env`
   di server). File ini tidak ikut git; di salinan baru, buat dari `edupad/secrets.example.h`.
4. Buka `edupad/edupad.ino`. Menu Tools:
   - Board: **ESP32S3 Dev Module**
   - PSRAM: **OPI PSRAM** (N16R8). Tanpa PSRAM, RAM bisa tidak cukup untuk koneksi HTTPS
     ("tidak bisa terhubung" padahal Wi-Fi dan server normal)
   - USB CDC On Boot: **Disabled** bila dicolok ke port **COM/UART**, **Enabled** bila ke port
     **USB** (kalau salah, Serial Monitor kosong)
   - Flash Size: **16MB (128Mb)** (N16R8; bawaannya 4MB)
   - Partition Scheme: **16M Flash (3MB APP/9.9MB FATFS)**. Sketch ~1,2 MB dengan animasi
     layar, sudah melewati batas partisi bawaan (1,25 MB) bila aset bertambah
5. Linux: supaya port bisa dipakai tanpa sudo (sekali saja, lalu logout/login):
   `sudo usermod -aG dialout $USER`
6. Upload, lalu buka Serial Monitor di 115200 baud.

## Wi-Fi

Saat menyala, EduPad mencoba Wi-Fi yang terakhir dipilih lewat hotspot (bila ada), lalu
Wi-Fi bawaan di `secrets.h`, masing-masing hingga 12 detik. Bila keduanya gagal, layar
menampilkan **Atur Wi-Fi** dan EduPad membuka hotspot:

1. Di HP, sambungkan ke Wi-Fi **EduPad-Setup** (sandi `edupad123`, ubah di `config.h`).
2. Halaman pengaturan biasanya terbuka sendiri; bila tidak, buka `http://192.168.4.1`.
3. Pilih jaringan, isi sandi, lalu **Simpan & sambungkan**. EduPad restart dan menyambung.

Tekan BOOT saat layar "Atur Wi-Fi" untuk mencoba lagi tanpa mengubah apa pun (mis. router baru
menyala). Pilihan dari hotspot tersimpan di flash dan tetap ada walau firmware di-upload ulang.

## Uji ke server di laptop

Jalankan `python -m edupad serve --host 0.0.0.0` di laptop, lalu di `secrets.h` isi
`EDUPAD_HOST` dengan IP laptop, `EDUPAD_PORT 8000`, dan `EDUPAD_TLS 0`.

## Bila ada masalah

| Gejala | Coba |
|---|---|
| Layar putih/hitam saja | Periksa CS/DC/RESET/SCK/MOSI; turunkan `TFT_SPI_HZ` ke 20000000 |
| Warna terbalik / merah jadi biru | `TFT_INVERT` / `TFT_BGR` di `config.h` |
| Meter suara diam saat bicara | Periksa SCK/WS/SD dan L/R; coba `MIC_USE_RIGHT_CHANNEL 1` |
| Selalu "Suara tidak terdengar" | Meter harus sering melewati garis kuning; naikkan gain: `MIC_GAIN_SHIFT 11` |
| Suara pecah / transkrip aneh | Gain terlalu besar: `MIC_GAIN_SHIFT 13` |
| "tidak bisa terhubung" + `[api] TLS:` di Serial | Cloudflare mungkin berganti CA: tambahkan root CA-nya di `edupad/certs.h` |
| Layar "Token perangkat salah" | `EDUPAD_DEVICE_TOKEN` di `secrets.h` tidak sama dengan server |
| `[mic] ... byte rekaman terbuang` | Wi-Fi lambat; dekatkan ke router |
| Layar "Speaker gagal" | Periksa BCLK/LRC/DIN amplifier |
| Status "Suara gagal diputar" | Lihat `[audio]` di Serial; HTTP 502 = kuota/kunci ElevenLabs di server |
| Suara tersendat | Naikkan `SPEAKER_PREBUFFER_MS` (mis. 600) |
