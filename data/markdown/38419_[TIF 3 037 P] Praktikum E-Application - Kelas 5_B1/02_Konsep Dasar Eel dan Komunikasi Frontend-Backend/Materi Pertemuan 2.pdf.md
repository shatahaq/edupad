---
course_id: "38419"
course: "[TIF 3 037 P] Praktikum E-Application - Kelas 5/B1"
pertemuan: 2
section: "Konsep Dasar Eel dan Komunikasi Frontend-Backend"
section_index: 2
title: "Pertemuan 2"
type: "resource"
source_file: "38419_[TIF 3 037 P] Praktikum E-Application - Kelas 5_B1/02_Konsep Dasar Eel dan Komunikasi Frontend-Backend/Materi Pertemuan 2.pdf"
source_url: "https://kelas.usu.ac.id/pluginfile.php/636275/mod_resource/content/1/Materi%20Pertemuan%202.pdf"
activity_url: "https://kelas.usu.ac.id/mod/resource/view.php?id=208251"
converter: "pymupdf4llm+ocr(8 hal)"
---

<!-- halaman 1 (OCR) -->

Aslab Teknik **HOME** Informatika K **Pertemuan 2 Praktikum E-Application**

**Nadya Lahfah Dhea Tri Lova Simanjuntak**

**HOME**

ABOUT

MORE

<!-- halaman 2 -->

**HOME**

ABOUT

MORE

## 1.Pemahaman Konsep Dasar Eel

Eel adalah library Python yang berfungsi sebagai jembatan untuk membangun aplikasi GUI desktop modern dengan memanfaatkan integrasi teknologi web. Python (Backend): Bertugas sebagai otak aplikasi untuk mengelola logika, perhitungan matematis, serta pengolahan data

HTML, CSS, dan JavaScript (Frontend): Bertugas menyusun antarmuka visual agar pengguna dapat berinteraksi langsung dengan aplikasi

**Peran Eel:** Menyatukan kedua sisi tersebut melalui koneksi internal, memungkinkan JavaScript memanggil fungsi Python dan sebaliknya tanpa memerlukan konfigurasi web server yang rumit

<!-- halaman 3 -->

**HOME**

ABOUT

MORE

## 2.Pengenalan Asynchronous

Pengembangan aplikasi dengan JavaScript, khususnya saat berkomunikasi dengan Python melalui Eel, kita menggunakan paradigma Asynchronous (async/await) **Kenapa perlu:**

Pemanggilan fungsi Python dari JavaScript tidak langsung menghasilkan jawaban

Python mungkin butuh waktu untuk menghitung, membaca file, atau mengolah data.

Kalau JavaScript langsung melanjutkan tanpa menunggu hasil maka yang ditampilkan bisa kosong atau error

<!-- halaman 4 -->

**HOME**

ABOUT

MORE

## 3.Pengenalan Synchronous

Synchronous (sinkron) berarti kode dieksekusi satu per satu, secara berurutan, dimana setiap operasi harus selesai sepenuhnya sebelum operasi berikutnya dimulai

Sifat pemblokiran ini memastikan setiap instruksi dijalankan sesuai urutan, tetapi dapat menyebabkan program menjadi tidak responsif jika ada tugas yang membutuhkan waktu lama, seperti permintaan data dari server, karena akan menunda eksekusi tugas selanjutnya

<!-- halaman 5 (OCR) -->

Aslab Teknik Informatika

**HOME**

ABOUT

MORE

Synchronous Asynchronous
1 1
20 seconds
20 seconds
2 2
7 seconds
7 seconds
3 3
10 seconds
Number of tasks Number of tasks
10 seconds
8 seconds
8 seconds
Total time taken by the tasks. Total time taken by the tasks.
45 seconds 20 seconds

<!-- halaman 6 (OCR) -->

Aslab Teknik Informatika

**HOME**

ABOUT

MORE

###### Asynchronous (Dengan await)

Synchronous (Tanpa await) Asynchronous (Dengan await) Berurutanbaris demi baris; tugas Bersamaan / non-blocking; program berikutnya harus menunggu tugas tidak terkunci saat menunggu tugas sebelumnya selesai. latar belakang.

###### Parameter Pola Eksekusi

latar belakang.

Respon Berisiko freeze atau tidak responsif jika Antarmuka tetap responsif dan lancar. Aplikasi proses Python berjalan lambat. Hasil Return Menghasilkan objek Promise (belum Menghasilkan data final yang siap ke JS berupa nilai konkret). langsung digunakan di UI. Efisiensi Waktu eksekusi bersifat akumulatif (total Waktu eksekusi dibatasi hanya oleh Waktu waktu = jumlah durasi seluruh tugas). durasi tugas terlama. Kapan Mengirim data satu arah tanpa butuh Mengambil nilai komputasi, kalkulasi Digunakan respon langsung (seperti logging atau matematika, query basis data, atau trigger background task). validasi form.

<!-- halaman 7 (OCR) -->

Aslab Teknik Informatika

**HOME**

<!DOCTYPE html> <htm1 1ang="en' <head>

<meta charset="UTF-8">

<meta name="viewport" content="width=device-width, initial-scale=1.0"> <title>Belajar Eel</title> <script type="text/javascript" src="/eel.js"></script> <script src="script.js"></script> </head> <body> <h1>Hitung Luas Persegi Panjang</h1> e == =dn > <input type="number" id="lebar" placeholder="Masukkan lebar" <button onclick="kirimData()">Hitung</button> <p>Hasil: <span id="hasil"></span></p> </body> </htm1>

ABOUT

###### MORE

**Inisialisasi Front End Untuk Program**

<!-- halaman 8 (OCR) -->

Aslab Teknik KInformatika

**HOME**

ABOUT

###### MORE

**Menghubungkan website kita ke bahasa pemrograman Python**

async function kirimData() let panjang = parseInt(document.getElementById("panjang").value) 1et 1ebar =parseInt(document.getElementById("lebar").value). let hasil await eel.hitung_luas(panjang, lebar)(). document.getElementById("hasil").innerText =hasil

<!-- halaman 9 (OCR) -->

Aslab Teknik Informatika

**HOME**

ABOUT

MORE

### import eel

eel.init("web")

@eel.expose def hitung_luas(panjang,lebar) 1ebar return panjang

eel.start("index.html")

**Lakukan Operasi Operasi di File python dengan elemen yang ada di Html**

<!-- halaman 10 (OCR) -->

## Aslab Teknik KInformatika

#### QUIZ TIME
**HOME**

ABOUT

MORE

##### Silahkan modifikasi kode program tersebut dimana harus menampilkan minimal 3 parameter
<!-- halaman 11 (OCR) -->

# K IlnrotikaAslab Teknik

Thank You!

**HOME**

ABOUT

MORE
