/** DATA DUMMY untuk Tutor, Equity Radar, dan Keuangan (hanya VITE_DATA_SOURCE=mock). */
import type { EquityData, FinanceData, TutorData } from "../types";

const DAY = 86_400_000;
const at = (daysAgo: number) => new Date(Date.now() - daysAgo * DAY).toISOString();
const date = (daysAgo: number) => at(daysAgo).slice(0, 10);

const topics: TutorData["topics"] = [
  { matkul: "Manajemen Sistem Basis Data", course_id: "1", pertemuan: 2, judul: "Database Engine & Indeks", penguasaan: 45, kuis: 2, skor_terakhir: 50, terakhir: at(1), ulang_pada: at(-1), jatuh_tempo: false },
  { matkul: "Pemrograman Visual", course_id: "2", pertemuan: 5, judul: "Percabangan If-Else", penguasaan: 62, kuis: 1, skor_terakhir: 67, terakhir: at(3), ulang_pada: at(0.1), jatuh_tempo: true },
  { matkul: "Sistem Pendukung Keputusan", course_id: "3", pertemuan: 3, judul: "Metode SAW", penguasaan: 90, kuis: 3, skor_terakhir: 100, terakhir: at(2), ulang_pada: at(-12), jatuh_tempo: false },
];

export const tutor: TutorData = {
  available: true,
  topics,
  courses: [
    { matkul: "Manajemen Sistem Basis Data", penguasaan: 45, topik: 1 },
    { matkul: "Pemrograman Visual", penguasaan: 62, topik: 1 },
    { matkul: "Sistem Pendukung Keputusan", penguasaan: 90, topik: 1 },
  ],
  dikuasai: 1,
  lemah: 1,
  jatuh_tempo: 1,
  rata_rata: 66,
  soal_30_hari: 14,
  soal_7_hari: 6,
  skor_7_hari: 58,
  miskonsepsi: [
    { teks: "WAL dikira mempercepat baca", jumlah: 2 },
    { teks: "Bobot SAW tidak dinormalisasi", jumlah: 1 },
  ],
  history: [
    {
      topic_key: "1:2",
      matkul: "Manajemen Sistem Basis Data",
      pertemuan: 2,
      judul: "Database Engine & Indeks",
      titik: [
        { waktu: at(9), skor: 33, bantuan: false },
        { waktu: at(6), skor: 50, bantuan: false },
        { waktu: at(4), skor: 67, bantuan: true },
        { waktu: at(1), skor: 83, bantuan: false },
      ],
    },
  ],
  help: [
    {
      id: "h1",
      judul: "Write-Ahead Logging",
      matkul: "Manajemen Sistem Basis Data",
      pertemuan: 2,
      status: "selesai",
      alasan: ["2 jawaban kuis belum tepat", "penguasaan 40%"],
      masalah: "Masih mengira WAL mempercepat pembacaan data",
      pelajaran: ["Bayangkan WAL seperti buku catatan kasir...", "Saat listrik padam...", "Jadi WAL menjaga data tetap aman..."],
      soal: 3,
      sebelum: 40,
      sesudah: 72,
      dibuat: at(5),
      selesai: at(4),
    },
  ],
  checks: [
    { matkul: "Manajemen Sistem Basis Data", pertemuan: 2, soal: "Apa fungsi buffer pool?", jawaban: "Cache halaman data di memori supaya jarang baca disk", penilaian: "benar", umpan_balik: "Tepat, buffer pool mengurangi I/O disk.", waktu: at(1) },
    { matkul: "Manajemen Sistem Basis Data", pertemuan: 2, soal: "Mengapa WAL penting untuk durability?", jawaban: "Supaya query lebih cepat", penilaian: "salah", umpan_balik: "WAL mencatat perubahan sebelum ditulis agar bisa dipulihkan.", waktu: at(1) },
  ],
};

export const equity: EquityData = {
  access: {
    mata_kuliah: [
      { matkul: "E-Application", course_id: "10", jenis: "teori", pertemuan_berlangsung: 7, pertemuan_bermateri: 0, materi_classroom: 0, tanpa_materi: [1, 2, 3, 4, 5, 6, 7].map((n) => ({ pertemuan: n, topik: null })), ocr: [], bisa_didengar: 0, status: "belum_ada_materi" },
      { matkul: "Pemrograman Visual", course_id: "2", jenis: "teori", pertemuan_berlangsung: 7, pertemuan_bermateri: 5, materi_classroom: 0, tanpa_materi: [{ pertemuan: 6, topik: "Perulangan" }, { pertemuan: 7, topik: "Array" }], ocr: [3], bisa_didengar: 5, status: "ada_kekosongan" },
      { matkul: "Sistem Pendukung Keputusan", course_id: "3", jenis: "teori", pertemuan_berlangsung: 7, pertemuan_bermateri: 7, materi_classroom: 2, tanpa_materi: [], ocr: [], bisa_didengar: 7, status: "lengkap" },
    ],
    jumlah_mata_kuliah: 3,
    tanpa_materi_sama_sekali: 1,
    pertemuan_berlangsung: 21,
    pertemuan_tanpa_materi: 9,
    cakupan_persen: 57,
    pertemuan_bermateri: 12,
    pertemuan_ocr: 1,
    bisa_didengar: 12,
  },
  attendance: [
    { matkul: "Praktikum Pemrograman Visual", course_id: "4", berlangsung: 7, hadir: 3, tidak_hadir: 4, persen: 43, pertemuan_semester: 16, jatah_tidak_hadir: 4, sisa_jatah: 0, status: "waspada", diperbarui: at(0) },
    { matkul: "Sistem Pendukung Keputusan", course_id: "3", berlangsung: 7, hadir: 7, tidak_hadir: 0, persen: 100, pertemuan_semester: 16, jatah_tidak_hadir: 4, sisa_jatah: 4, status: "aman", diperbarui: at(0) },
  ],
  warnings: [
    { jenis: "kehadiran", tingkat: "sedang", matkul: "Praktikum Pemrograman Visual", pesan: "Jatah tidak hadir Praktikum Pemrograman Visual tinggal 0 kali. Usahakan hadir di pertemuan berikutnya.", kunci: "hadir:4:4" },
    { jenis: "anggaran", tingkat: "sedang", matkul: null, pesan: "Anggaran Makan tinggal Rp40.000 (92% terpakai).", kunci: "anggaran:Makan" },
  ],
  mastery: tutor,
  voice: { questions_30d: 86, listenable_meetings: 12, meetings_with_material: 12 },
  rules: { semester_meetings: 16, min_attendance: 0.75 },
  accessibility: {
    voice_mode: true,
    speed: "cepat",
    listenable_meetings: 12,
    meetings_with_material: 12,
    ocr_pages: 46,
    ocr_meetings: 3,
    questions_30d: 86,
    answers_spoken_30d: 64,
    alerts_spoken_30d: 21,
  },
};

export const finance: FinanceData = {
  available: true,
  transactions: [
    { id: "t1", kind: "expense", amount: 25000, category: "Makan", note: "nasi goreng", occurred_on: date(0), source: "suara", created_at: at(0) },
    { id: "t2", kind: "income", amount: 1000000, category: "Kiriman keluarga", note: "dari ibu", occurred_on: date(2), source: "dashboard", created_at: at(2) },
    { id: "t3", kind: "expense", amount: 15000, category: "Transportasi", note: "ojek ke kampus", occurred_on: date(1), source: "suara", created_at: at(1) },
  ],
  budgets: { Makan: 500000, Transportasi: 150000 },
  expense_categories: ["Makan", "Transportasi", "Tempat tinggal", "Kuliah", "Internet", "Kesehatan", "Hiburan", "Lainnya"],
  income_categories: ["Kiriman keluarga", "Beasiswa", "Kerja sampingan", "Pengembalian", "Lainnya"],
};
