# EduPad AI Office Frontend

React + TypeScript + Vite, Tailwind CSS, dan Phaser 3.

```powershell
npm install
npm run dev
```

Untuk memeriksa map dan animasi PIXEL tanpa koneksi backend, buka URL Vite dengan
`?preview=1`, misalnya `http://localhost:5173/?preview=1`. Mode ini tidak mengirim task ke API.

Vite meneruskan `/api` ke Office API di `http://127.0.0.1:8001`. Bila API belum aktif,
dashboard menampilkan data preview dengan label yang jelas. Saat API aktif, snapshot dan SSE
menjadi sumber status robot, tugas, dan activity feed.

Untuk vertical slice indexing, jalankan juga `python -m edupad office-worker` dari root proyek.
Task `index` akan di-claim worker, menjalankan fungsi indexing EduPad yang asli, lalu mengirim
status PIXEL dan workstation `knowledge-index-01` ke Phaser.

Visual kantor memakai shell ruangan yang tenang dan atlas furnitur transparan pada
`public/assets/office/`, bukan satu gambar penuh. Phaser menempatkan meja, server, tanaman, dan
objek lain sebagai sprite terpisah serta mengurutkannya berdasarkan koordinat Y. Karena agent
berada pada lapisan kedalaman yang sama, mereka terlihat berjalan di depan atau di belakang
furnitur sesuai posisinya. Prompt aset didokumentasikan di `ASSET_PROMPTS.md`.

Dinding depan dan pembatas memakai aset transparan terpisah yang dipecah menjadi beberapa
occlusion band. Setiap band memiliki depth sesuai koordinat Y, sehingga agent di balik dinding
tertutup oleh fasad, agent di koridor tampil di depannya, dan pintu tetap menjadi celah yang
dapat dilewati.

Furniture menggunakan interaction-edge depth sehingga karakter selalu terlihat di depannya;
hanya fasad dinding yang dapat menutup bagian karakter. Perjalanan antar-ruangan memakai
waypoint interior-pintu-koridor-pintu dari `src/game/navigation.ts`, bukan garis lurus, agar
agent mengikuti tapak koridor dan tidak memotong dinding secara diagonal.

Ukuran furniture dihitung dengan satu faktor skala uniform berdasarkan bounding box asli,
sehingga barang yang diperkecil tidak pernah gepeng. Enam patrol loop idle membawa setiap agent
keluar melalui pintu dan kembali ke ruang asal. Patrol tervalidasi memiliki jarak aman 18 px dari
bounding box furniture melalui `npm run validate:office`. Validator yang sama memeriksa benturan
antar-furniture, batas aman setiap ruangan, dan enam jalur pintu agar dekorasi baru tidak menutup
akses agent.

Saat backend menyatakan agent `idle`, agent memilih titik aman di ruangan asal dan berjalan
santai setelah jeda acak. Idle roaming ini hanya state visual: event backend baru selalu
membatalkannya. State `running` tetap menentukan perjalanan ke workstation dan animasi kerja.

Animasi kerja dipilih berdasarkan peran: Coordinator, Researcher/PIXEL, dan Analyst duduk
mengetik; Planner memeriksa dokumen; Tutor berdiri menjelaskan; Keeper menangani panel server.
Semua animasi ini hanya aktif ketika backend mengirim state `running`.

Gelembung percakapan di atas setiap agent menjelaskan aktivitasnya. Saat ada pekerjaan,
teksnya berasal dari task/status backend; saat idle, teks mengikuti aktivitas visual seperti
membaca materi, mengecek konsol, atau berkeliling kantor. Warna bingkai tetap mengikuti state
backend, sehingga state visual berjalan tidak mengubah atau memalsukan hasil pekerjaan.

Saat tidak ada pekerjaan, seluruh enam agent bergantian antara patrol luar dan aktivitas idle
sesuai peran: NOVA memeriksa konsol, PIXEL/TEMPO membaca dokumen, SORA berlatih menjelaskan,
METRIC memeriksa dashboard, dan NEXUS merawat panel server. Seluruh aktivitas idle langsung
dibatalkan ketika event backend baru diterima. Dalam mode preview keenam agent berada dalam
state `idle` agar siklus patrol dapat diperiksa. PIXEL bermarkas di Research Lab dan hanya
berpindah ke Knowledge Server ketika event backend indexing menetapkan workstation
`knowledge-index-01`.

Nama ruangan tersembunyi saat peta tidak disentuh dan muncul ketika pointer berada di dalam
area ruangan. Klik atau tap agent untuk membuka kartu identitas berisi visual bot, nama, peran,
deskripsi tanggung jawab, ruangan, status backend, dan aktivitas terakhir.

Phaser memotong atlas furnitur v2 menjadi frame 384x384 dan tiga sheet PIXEL menjadi grid 4x4
saat runtime. Atlas furnitur v2 memiliki gutter transparan tervalidasi agar meja, monitor,
tanaman, dan kursi tidak terpotong atau bocor ke frame sebelah. Peta lama
`edupad-office-map-v1.png` tetap disimpan sebagai referensi/fallback aset dan tidak ditimpa.
Bank server pada frame furnitur dipotong lagi menjadi empat kolom rak individual saat runtime,
lalu disusun rapat tanpa memperbesar atau mengubah rasio pixel art aslinya.

Tombol `Atur furnitur` mengaktifkan editor posisi khusus sprite furnitur. Furnitur dapat diseret
dengan snap 4 px dan koordinatnya disimpan di `localStorage` browser; bot, dinding, pintu, dan
ruangan tidak ikut dapat dipindahkan. `Reset posisi` menghapus susunan lokal dan mengembalikan
seluruh furnitur ke layout bawaan. Fitur ini tidak menulis ke Office API atau Supabase.

Keenam agent menggunakan rig spritesheet yang sama dengan tint identitas masing-masing. State
`succeeded` dan `failed` tetap ditampilkan di workstation sebelum agent kembali idle pada event
berikutnya.
