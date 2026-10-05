---
course_id: "38418"
course: "[TIF 3 037 P] Praktikum E-Application - Kelas 5/A1"
pertemuan: 1
section: "Pengenalan E-Application dan Eel"
section_index: 1
title: "pertemuan 1"
type: "resource"
source_file: "38418_[TIF 3 037 P] Praktikum E-Application - Kelas 5_A1/01_Pengenalan E-Application dan Eel/Pertemuan 1.pdf"
source_url: "https://kelas.usu.ac.id/pluginfile.php/636488/mod_resource/content/3/Pertemuan%201.pdf"
activity_url: "https://kelas.usu.ac.id/mod/resource/view.php?id=208433"
converter: "pymupdf4llm+ocr(8 hal)"
---

<!-- halaman 1 (OCR) -->

# Aslab Teknik **HOME** Informatika K **Pertemuan 1 Praktikum E-Application**

**HOME**

ABOUT

MORE

**Nadya Lahfah Dhea Tri Lova Simanjuntak**

<!-- halaman 2 -->

**HOME**

ABOUT

MORE

## 1. Apa itu E-Application

E-Application (Electronic Application) adalah aplikasi yang dikembangkan dengan memanfaatkan teknologi digital untuk membantu pengguna menyelesaikan berbagai pekerjaan secara lebih efektif dan efisien.

Pada mata kuliah ini, E-Application berfokus pada pengembangan aplikasi desktop menggunakan library Eel pada Python, yang memungkinkan integrasi langsung antara Python dan antarmuka berbasis HTML. Melalui Eel, mahasiswa dapat mengembangkan aplikasi yang memanfaatkan Python sebagai backend dan HTML, CSS, serta JavaScript sebagai frontend.

<!-- halaman 3 -->

**HOME**

ABOUT

MORE

2. Apa itu GUI?

GUI adalah antarmuka grafis yang memungkinkan pengguna berinteraksi dengan komputer menggunakan elemen visual, seperti tombol, ikon, menu, dan jendela.

Contoh GUI dalam Kehidupan Sehari-hari

File Explorer

Telegram

Calculator

Microsoft Word Spotify

<!-- halaman 4 -->

**HOME**

ABOUT

MORE

3. Apa itu Eel?

Eel adalah library Python yang berfungsi sebagai jembatan untuk membuat aplikasi desktop dengan tampilan berbasis web. Dengan Eel, kita dapat menggunakan HTML, CSS, dan JavaScript untuk membuat antarmuka (frontend), sedangkan Python digunakan untuk mengelola logika dan pemrosesan data (backend).

<!-- halaman 5 -->

**HOME**

ABOUT

MORE

## 4.Framework GUI

### 2 **. Kivy**

1. **Electron JS** Electron JS adalah framework berbasis JavaScript yang digunakan untuk mengembangkan aplikasi desktop dengan memanfaatkan teknologi web, seperti HTML, CSS, dan JavaScript. Framework ini banyak digunakan untuk membangun aplikasi modern.

Kivy adalah framework open-source berbasis Python yang digunakan untuk membuat aplikasi GUI pada berbagai platform, seperti desktop, perangkat seluler, dan perangkat layar sentuh. Kivy dikenal karena mampu menghasilkan tampilan yang modern, responsif, dan interaktif.

<!-- halaman 6 -->

**HOME**

ABOUT

MORE

## 4.Framework GUI

### 3. **Java Swing**

Java Swing adalah library bawaan Java yang digunakan untuk membuat aplikasi desktop berbasis GUI. Swing menyediakan berbagai komponen, seperti tombol, menu, tabel, dan formulir, sehingga memudahkan pengembang dalam membangun aplikasi desktop.

<!-- halaman 7 -->

**HOME**

ABOUT

MORE

## 5.Instalasi Environment

### VS CODE
### PYTHON
Vscode kita jadikan IDE yang ideal sebagai medium kita menjalankan banyak bahasa pemrograman yang efisien

Memastikan Enviroment Komputer sudah terinstal Python agar dapat langsung digunakan (install juga extension jika mau)

**PIP** Package manager pada Python digunakan untuk menginstal berbagai library tambahan. Modul menjelaskan bahwa pip digunakan untuk mengakses library yang ada di Python

**EEL**

Mengintall Library Eel di Command Prompt agar dapat langsung terinstall didesktop dan siap dipanggil atau di import pada Project kita

<!-- halaman 8 (OCR) -->

Aslab Teknik Informatika

**HOME**

ABOUT

MORE

https://www.python.org/downloads/ (Mengintall Python) C:\Users\ASUS>python--version Python 3.13.2

Menginstall dan Menjalankan pip C:\Users\ASUS>pip --version pip 25.0.1 from C:\Users\ASUS\AppData\Local\Programs\Python\Python313\Lib\site-packages\pip (python 3.13) Menginstall Eel pada library python kamu D:\>pip install eel Collecting eel Downloading eel-0.18.2.tar.gz (26 kB) Installing build dependencies ...done Getting requirements to build wheel done Preparing metadata (pyproject.toml) done

<!-- halaman 9 (OCR) -->

Aslab Teknik Informatika

MORE

**HOME**

ABOUT

#### Menginstall Eel pada library python kamu

D:\>pip show eel Name: Eel Version: 0.18.2 Summary: For little HTML GUI applications, with easy Python/JS interop Home-page: https://github.com/python-eel/Eel Author: PythonEel Organisation Author-email: python-eel@protonmail.com License:

Location:C:\Users\ASUS\AppData\Local\Programs\Python\Python313\Lib\site-packages Requires: bottle, bottle-websocket, future, importlib_resources, pyparsing, typing_extensions Required-by:

D:\>pip list Package Version altair 6.1.0 anyio 4.8.0 argon2-cffi 23.1.0 argon2-cffi-bindings 21.2.0

Version

<!-- halaman 10 (OCR) -->

Aslab Teknik Informatika

**HOME**

ABOUT MORE

### 6.Membuat Project awal Eel

Pertemuan 1 Praktikum EAPP web 5 index.html JS index.js css style.css main.py

Membuat Folder dengan Ketentuan dan struktur seperti ini di Vscode

<!-- halaman 11 (OCR) -->

Aslab Teknik VInformatika

**HOME** ABOUT MORE

### 6.Membuat Project awal Eel

web main.py import eel

Karna kita menggunakan basis html maka pada kode python kita, kita memanggil HTML yang pertama kali ditampilkan didalam Aplikasi Kita

eel.init('web") eel.start('index.html')

<!-- halaman 12 -->

**HOME**

ABOUT

MORE

## 6.Membuat Project awal Eel

Untuk Sekarang Eel Telah menciptakan sebuah aplikasi yang dapat berjalan sendiri (tanpa bantuan chrome, edge atau mesin website lain) namun masih tak memiliki tampilan, maka tambahkan tampilan awal pada file html kita

<!-- halaman 13 (OCR) -->

###### Aslab Teknik Informatika

**HOME**

ABOUT MORE

6.Membuat Project awal Eel PS C:\Users\HP\Downloads\Pertemuan 1 Praktikum EAPP> python main.py

Pertemuan 1 E-app

Sekarang kamu sudah memiliki aplikasi kamu sendiri yang dapat berjalan sendiri tanpa berjalan di browsere manapun

halo kata

<!-- halaman 14 (OCR) -->

###### Aslab Teknik Informatika

### QUIZ TIME
Profil D3 TI USU

##### Teknik Informatika

**HOME**

ABOUT

MORE

Program Studi Diploma (D3)

Program Diploma Teknik Informatika di Universitas Sumatera Utara (USU) didirikan pada tahun 2001 dan telah menjadi program unggulan dalam pendidikan vokasi di bidang teknik informatika Program Studi D3 Teknik Informatika Terakreditasi Baik Sekali

No.059/SK/LAM-INFOKOM/Ak/D3/XII/2022

<!-- halaman 15 (OCR) -->

## K IlnrotikaAslab Teknik

Thank You!

**HOME**

ABOUT

MORE
