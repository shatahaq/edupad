# Manajemen Waktu & Penjadwalan Proyek: Gantt Chart

Sumber: https://kelas.usu.ac.id/course/view.php?id=38403&section=5

TIK2111 • PERTEMUAN 5

Program Studi D3 Teknik Informatika — Fakultas Vokasi USU

# Manajemen Waktu & Penjadwalan Proyek: Gantt Chart

## Definisi Aktivitas, Estimasi Durasi, Dependensi, dan Visualisasi Jadwal Proyek TI

👨‍🏫 **Pengampu:** Zulhamsyah Fachrurrazi Nasution, S.Kom., M.MSI

🔄 Rekap Pertemuan Sebelumnya

✔ **Ruang Lingkup Proyek:** Batasan pekerjaan yang harus & tidak dikerjakan.

✔ **Scope Creep:** Risiko pembengkakan scope yang dicegah via formal change control.

✔ **Work Breakdown Structure:** Dekomposisi proyek menjadi work package terukur.

### 🎯 Capaian Pembelajaran (Sub-CPMK 4)

Mahasiswa mampu menyusun penjadwalan proyek menggunakan Gantt Chart.

**📌 Indikator Pencapaian Pertemuan Ini:**

- Menjelaskan proses manajemen waktu proyek dan hubungan antaraktivitas.
- Menjelaskan teknik estimasi durasi aktivitas proyek.
- Menyusun Gantt Chart untuk studi kasus proyek TI.

### ⏳ 1. Proses Manajemen Waktu Proyek & Dependensi Aktivitas

**Manajemen Waktu Proyek:** Proses yang dibutuhkan untuk mengelola penyelesaian proyek secara tepat waktu, meliputi perencanaan, penyusunan, dan pengendalian jadwal.

👉 Jadwal proyek yang baik menjadi acuan bersama bagi tim untuk memantau kemajuan pekerjaan dari waktu ke waktu.

#### 🔄 5 Proses Utama Manajemen Waktu Proyek

**1. Definisikan Aktivitas**
Uraikan Work Package WBS ke daftar aktivitas spesifik.

**2. Urutkan Aktivitas**
Tentukan hubungan/keterkaitan antaraktivitas.

**3. Estimasi Durasi**
Hitung estimasi periode waktu tiap aktivitas.

**4. Susun Jadwal**
Integrasikan aktivitas, durasi, & sumber daya ke timeline.

**5. Kendalikan Jadwal**
Pantau & kelola perubahan jadwal (iteratif).

#### 🔗 4 Jenis Dependensi Antaraktivitas

**Finish-to-Start (FS)**
Aktivitas B baru dapat dimulai setelah Aktivitas A selesai (paling umum).

**Start-to-Start (SS)**
Aktivitas B dapat dimulai bersamaan dengan dimulainya Aktivitas A.

**Finish-to-Finish (FF)**
Aktivitas B harus selesai bersamaan dengan selesainya Aktivitas A.

**Start-to-Finish (SF)**
Aktivitas B harus selesai sebelum Aktivitas A dimulai (jarang digunakan).

### 📏 2. Teknik Estimasi Durasi Aktivitas

#### 🎓 Expert Judgment

Estimasi berdasarkan penilaian dan pengalaman langsung dari ahli/praktisi terampil.

#### 📂 Analogous Estimating

Estimasi berdasarkan durasi historis dari aktivitas serupa pada proyek masa lalu.

#### 📊 Parametric Estimating

Menggunakan hubungan statistik antara data historis dan variabel/parameter lain.

#### 📐 Three-Point Estimating (PERT)

Memperhitungkan 3 skenario: Optimis, Pesimis, dan Paling Mungkin (Most Likely).

### 📊 3. Gantt Chart: Anatomi, Kelebihan & Tools

**Gantt Chart:** Diagram batang yang menampilkan jadwal proyek, memperlihatkan tanggal mulai dan selesai setiap aktivitas sepanjang garis waktu. Diperkenalkan oleh Henry Gantt pada awal abad ke-20.

#### 🧩 Anatomi Gantt Chart

**📋 Task List:** Daftar aktivitas terstruktur pada kolom kiri diagram.

**📊 Timeline Bar:** Batang horizontal penanda durasi & posisi waktu.

**♦️ Milestone:** Titik pencapaian penting (durasi 0, simbol berlian).

**➡️ Dependency Arrow:** Garis panah penghubung keterkaitan antaraktivitas.

##### 👍 Kelebihan Gantt Chart

- Sangat mudah dipahami secara visual oleh berbagai stakeholder.
- Memperlihatkan keseluruhan jadwal proyek secara ringkas.
- Sangat cocok untuk memantau progres riil terhadap rencana.

##### 👎 Keterbatasan Gantt Chart

- Kurang efektif memetakan jalur kritis pada proyek yang sangat kompleks.
- Kerap sulit menampilkan dependensi rumit antar banyak aktivitas.
- Perlu pembaruan secara rutin agar data tetap akurat.

**🛠️ Tools Populer Pembuat Gantt Chart:**

Microsoft Project
MS Excel / Google Sheets
GanttProject (Gratis)
Trello (Timeline View)
Asana / ClickUp
Jira (Roadmap)

### 💻 Studi Kasus: Portal Berita Kampus (Target 8 Minggu)

**Rincian Durasi & Aktivitas Proyek:**

- Analisis kebutuhan: 1 minggu
- Desain sistem: 2 minggu
- Pengembangan Front-End & Back-End: 3 minggu (dapat berjalan paralel)
- Pengujian (Testing): 1 minggu
- Peluncuran (Launch): 1 minggu

👉 **Diskusi Kelompok (±5 Menit):** Tentukan minggu mulai/selesai tiap aktivitas, identifikasi pekerjaan paralel, dan tentukan 1 milestone kunci peluncuran!

#### 📌 Tautan Modul & Aktivitas Pertemuan 5:

**[📄 Slide Materi & Bahan Ajar](https://kelas.usu.ac.id/pluginfile.php/556992/course/section/583850/MPIT5.pptx "📄 Slide Materi & Bahan Ajar")**
