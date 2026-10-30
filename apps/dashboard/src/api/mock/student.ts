/**
 * DATA DUMMY halaman mahasiswa (presensi, tugas, jadwal, percakapan, riwayat belajar).
 *
 * Bentuk meniru data asli (data/schedule/*.json, data/assignments/assignments.json, Supabase
 * agent_sessions/agent_turns/agent_memories) tetapi isinya karangan: tidak ada NIM atau nama
 * dosen sungguhan. Waktu dihitung relatif terhadap sekarang (WIB) sehingga selalu ada presensi
 * yang sedang dibuka, tugas yang mendekati deadline, dst.
 */
import type {
  AssignmentsData,
  AttendanceData,
  AttendanceMeeting,
  ClassSlot,
  ConversationSession,
  ConversationsData,
  LearningData,
  ScheduleData,
  Task,
  Weekday,
} from "../types";

const MIN = 60_000;
const HOUR = 60 * MIN;
const DAY = 24 * HOUR;
const WIB_OFFSET = 7 * HOUR;
const now = Date.now();

const WEEKDAYS: Weekday[] = ["minggu", "senin", "selasa", "rabu", "kamis", "jumat", "sabtu"];

/** Tanggal & jam WIB dari epoch ms. */
function wib(ms: number) {
  const d = new Date(ms + WIB_OFFSET);
  const pad = (n: number) => String(n).padStart(2, "0");
  return {
    date: `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}`,
    hhmm: `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}`,
    weekday: WEEKDAYS[d.getUTCDay()],
  };
}

/** ISO dengan zona +07:00, seperti di attendance.json. */
const isoWib = (ms: number) => {
  const w = wib(ms);
  return `${w.date}T${w.hhmm}+07:00`;
};

/** Bulatkan ke 10 menit agar jam terlihat wajar. */
const round10 = (ms: number) => Math.round(ms / (10 * MIN)) * 10 * MIN;

/** Epoch ms untuk tanggal WIB + "HH:MM". */
const atWib = (date: string, hhmm: string) => Date.parse(`${date}T${hhmm}:00+07:00`);

function rng(seed: number) {
  return () => {
    seed = (seed * 1664525 + 1013904223) % 2 ** 32;
    return seed / 2 ** 32;
  };
}

/* ---------- mata kuliah & jadwal ---------- */

interface Course {
  kode: string;
  course: string;
  short: string;
  jenis: "teori" | "praktikum";
  kelas: string;
  sks: number;
  ruang: string;
  nama_ruang: string;
  dosen: string[];
}

const COURSES: Course[] = [
  { kode: "TIF 3 031", course: "Pemrograman Visual", short: "PV", jenis: "teori", kelas: "5/B", sks: 2, ruang: "I05.2.1.4", nama_ruang: "Ruang I05.2.1.4", dosen: ["Dr. Andi Pratama, M.Kom."] },
  { kode: "TIF 3 031 P", course: "Praktikum Pemrograman Visual", short: "Prak. PV", jenis: "praktikum", kelas: "5/B1", sks: 1, ruang: "I09.3.3.6", nama_ruang: "Laboratorium Komputer", dosen: ["Rina Wulandari, M.Kom."] },
  { kode: "TIF 3 030", course: "Manajemen Sistem Basis Data", short: "MSBD", jenis: "teori", kelas: "5/B", sks: 2, ruang: "I05.2.1.6", nama_ruang: "Ruang I05.2.1.6", dosen: ["Budi Santoso, M.T."] },
  { kode: "TIF 3 030 P", course: "Praktikum Manajemen Sistem Basis Data", short: "Prak. MSBD", jenis: "praktikum", kelas: "5/B1", sks: 1, ruang: "I09.3.3.5", nama_ruang: "Laboratorium Basis Data", dosen: ["Sari Lestari, M.Kom."] },
  { kode: "TIF 3 033", course: "Manajemen Proyek IT", short: "MPIT", jenis: "teori", kelas: "5/B", sks: 3, ruang: "I05.2.2.1", nama_ruang: "Ruang I05.2.2.1", dosen: ["Dr. Hendra Gunawan, M.Sc."] },
  { kode: "TIF 3 035", course: "E-Application", short: "E-App", jenis: "teori", kelas: "5/B", sks: 2, ruang: "I05.2.1.2", nama_ruang: "Ruang I05.2.1.2", dosen: ["Dewi Anggraini, M.Kom."] },
  { kode: "TIF 3 029 P", course: "Praktikum Sistem Pendukung Keputusan", short: "Prak. SPK", jenis: "praktikum", kelas: "5/B1", sks: 1, ruang: "I09.3.3.6", nama_ruang: "Laboratorium Komputer", dosen: ["Fajar Nugroho, M.Kom."] },
];

const byShort = (short: string) => COURSES.find((c) => c.short === short)!;

/** Jadwal mingguan tetap (selain hari ini, yang dibentuk dari presensi di bawah). */
const WEEK: { hari: Weekday; short: string; mulai: string; selesai: string }[] = [
  { hari: "senin", short: "MSBD", mulai: "08:00", selesai: "09:40" },
  { hari: "senin", short: "Prak. SPK", mulai: "13:30", selesai: "15:10" },
  { hari: "selasa", short: "PV", mulai: "08:00", selesai: "09:40" },
  { hari: "selasa", short: "MPIT", mulai: "10:30", selesai: "13:00" },
  { hari: "rabu", short: "Prak. PV", mulai: "09:00", selesai: "10:40" },
  { hari: "rabu", short: "E-App", mulai: "13:30", selesai: "15:10" },
  { hari: "kamis", short: "Prak. MSBD", mulai: "08:00", selesai: "09:40" },
  { hari: "kamis", short: "MSBD", mulai: "10:30", selesai: "11:20" },
  { hari: "jumat", short: "MPIT", mulai: "08:00", selesai: "09:40" },
  { hari: "jumat", short: "PV", mulai: "14:00", selesai: "15:40" },
];

const slot = (hari: Weekday, short: string, mulai: string, selesai: string): ClassSlot => {
  const { short: _s, ...c } = byShort(short);
  void _s;
  return { hari, mulai, selesai, ...c };
};

/* ---------- presensi hari ini (relatif terhadap sekarang) ---------- */

const today = wib(now);

/** Tiga pertemuan "hari ini": sudah diisi, sedang dibuka, dan nanti. */
const TODAY_PLAN = [
  { short: "MSBD", from: -5 * HOUR, to: -3 * HOUR - 20 * MIN, pertemuan: 6, topik: "Normalisasi 3NF dan BCNF", status: "hadir" as const, cara: ["QR", "langsung"] as const },
  { short: "PV", from: -50 * MIN, to: 40 * MIN, pertemuan: 6, topik: "Event handling dan delegasi", status: null, cara: ["QR"] as const },
  { short: "Prak. PV", from: 3 * HOUR, to: 4 * HOUR + 40 * MIN, pertemuan: 6, topik: "Form dan validasi input", status: null, cara: ["langsung"] as const },
];

function meeting(short: string, start: number, end: number, pertemuan: number, topik: string | null, status: "hadir" | null, cara: readonly ("QR" | "langsung")[]): AttendanceMeeting {
  const c = byShort(short);
  const window = status ? "sudah_diisi" : now < start ? "belum_dibuka" : now <= end ? "dibuka" : "tutup";
  return {
    id: `mock-${short}-${pertemuan}`.replace(/\W+/g, "-").toLowerCase(),
    course: c.course,
    kode: c.kode,
    kelas: c.kelas,
    pertemuan,
    topik,
    mulai: isoWib(start),
    selesai: isoWib(end),
    status,
    window,
    cara: [...cara],
  };
}

const todayMeetings = TODAY_PLAN.map((p) => meeting(p.short, round10(now + p.from), round10(now + p.to), p.pertemuan, p.topik, p.status, p.cara));

/* Dekat tengah malam sebagian rencana jatuh ke hari lain; yang bukan hari ini tidak dihitung "hari ini". */
const todayOnly = todayMeetings.filter((m) => m.mulai!.slice(0, 10) === today.date);

const upcoming: AttendanceMeeting[] = [];
for (let d = 1; d <= 7; d++) {
  const day = wib(now + d * DAY);
  WEEK.filter((w) => w.hari === day.weekday).forEach((w, i) => {
    upcoming.push(meeting(w.short, atWib(day.date, w.mulai), atWib(day.date, w.selesai), 7 + Math.floor(d / 7), i === 0 ? "Pembahasan lanjutan" : null, null, ["QR", "langsung"]));
  });
}
upcoming.sort((a, b) => a.mulai!.localeCompare(b.mulai!));

const RECAP: Record<string, [number, number]> = {
  PV: [5, 6],
  "Prak. PV": [5, 5],
  MSBD: [6, 6],
  "Prak. MSBD": [4, 5],
  MPIT: [5, 6],
  "E-App": [4, 6],
  "Prak. SPK": [5, 5],
};

export const attendance: AttendanceData = {
  updated_at: isoWib(round10(now - 25 * MIN)),
  stale: false,
  today: todayOnly,
  upcoming,
  recap: COURSES.map((c) => ({ course: c.course, kode: c.kode, kelas: c.kelas, hadir: RECAP[c.short][0], pertemuan: RECAP[c.short][1] })),
};

/* Jadwal: minggu tetap, tetapi hari ini memakai jam pertemuan di atas agar Beranda konsisten. */
export const schedule: ScheduleData = {
  updated_at: isoWib(round10(now - 9 * HOUR)),
  classes: [
    ...WEEK.filter((w) => w.hari !== today.weekday).map((w) => slot(w.hari, w.short, w.mulai, w.selesai)),
    ...TODAY_PLAN.map((p, i) => ({ p, m: todayMeetings[i] }))
      .filter(({ m }) => m.mulai!.slice(0, 10) === today.date)
      .map(({ p, m }) => slot(today.weekday, p.short, m.mulai!.slice(11, 16), m.selesai!.slice(11, 16))),
  ],
};

/* ---------- tugas ---------- */

function task(id: string, short: string, jenis: Task["jenis"], judul: string, pertemuan: number | null, deadlineIn: number | null, extra: Partial<Task> = {}): Task {
  const c = byShort(short);
  const deadline = deadlineIn == null ? null : round10(now + deadlineIn);
  return {
    id,
    course: c.course,
    kode: c.kode,
    jenis,
    judul,
    pertemuan,
    dibuka: deadline == null ? null : isoWib(deadline - 7 * DAY),
    deadline: deadline == null ? null : isoWib(deadline),
    submitted: false,
    late_submission: false,
    overdue: deadline != null && deadline < now,
    graded: false,
    nilai: null,
    url: `https://kelas.usu.ac.id/mod/${jenis === "kuis" ? "quiz" : "assign"}/view.php?id=${id}`,
    soal: "",
    ...extra,
  };
}

export const assignments: AssignmentsData = {
  updated_at: isoWib(round10(now - 40 * MIN)),
  tasks: [
    task("206120", "PV", "tugas", "Tugas 5: Aplikasi kalkulator dengan event handler", 5, 5 * HOUR, {
      soal: "Buat aplikasi kalkulator sederhana memakai Windows Forms. Setiap tombol angka memakai satu event handler yang sama (delegasi). Kumpulkan file .zip proyek dan tangkapan layar.",
    }),
    task("206134", "MSBD", "tugas", "Latihan normalisasi sampai 3NF", 6, 2 * DAY + 3 * HOUR, {
      soal: "Diberikan tabel PEMINJAMAN(no_pinjam, nim, nama, kode_buku, judul, tgl_pinjam). Tentukan ketergantungan fungsional lalu normalisasikan sampai 3NF. Sertakan alasan setiap langkah.",
    }),
    task("198402", "E-App", "kuis", "Kuis 2: Arsitektur e-commerce", 4, 4 * DAY, { soal: "Kuis pilihan ganda 15 soal, waktu 20 menit, satu kali percobaan." }),
    task("206010", "Prak. SPK", "tugas", "Praktik 4: Komponen dasar SPK", 4, -1 * DAY - 2 * HOUR, {
      soal: "Jelaskan hubungan antarkomponen pada gambar arsitektur Sistem Pendukung Keputusan: data management, model management, user interface, dan knowledge base.",
    }),
    task("205877", "MPIT", "tugas", "Project charter kelompok", 3, -3 * DAY, { submitted: true, soal: "Susun project charter untuk proyek kelompok: tujuan, ruang lingkup, stakeholder, jadwal awal, dan risiko." }),
    task("205640", "Prak. MSBD", "tugas", "Modul 4: Stored procedure", 4, -6 * DAY, { submitted: true, late_submission: true, soal: "Buat tiga stored procedure untuk basis data perpustakaan sesuai modul." }),
    task("205101", "Prak. PV", "tugas", "Modul 3: Layout dan kontrol dasar", 3, -12 * DAY, { submitted: true, graded: true, nilai: "88,00 / 100,00", soal: "Rancang form pendaftaran dengan TableLayoutPanel." }),
    task("198314", "Prak. SPK", "kuis", "Algoritma pemilihan tempat kos", 1, null, { soal: "Kuis tanpa batas waktu; satu kali percobaan." }),
  ],
};

/* ---------- percakapan ---------- */

const pv = todayMeetings[1];
const hhmm = (iso: string | null) => (iso ? iso.slice(11, 16).replace(":", ".") : "—");
const nextTask = assignments.tasks[0];
/** "hari ini" / "besok" agar teks jawaban cocok dengan jam mock (dekat tengah malam). */
const when = (iso: string | null) => (iso?.slice(0, 10) === today.date ? "hari ini" : "besok");
const prak = todayMeetings[2];
const COUNT = ["tidak ada", "satu", "dua", "tiga"];

let turnId = 900;
const turn = (agoMs: number, t: Omit<ConversationSession["turns"][number], "id" | "at">) => ({ id: turnId++, at: new Date(now - agoMs).toISOString(), ...t });

export const conversations: ConversationsData = {
  sessions: [
    {
      id: 214,
      started_at: new Date(now - 34 * MIN).toISOString(),
      last_active: new Date(now - 6 * MIN).toISOString(),
      summary: null,
      turns: [
        turn(34 * MIN, {
          question: "Ada absen apa aja hari ini?",
          speech:
            `Hari ini ada ${COUNT[todayOnly.length]} presensi. MSBD sudah kamu isi. Pemrograman Visual sedang dibuka sampai jam ${hhmm(pv.selesai)}, lewat QR.` +
            ` Praktikum PV dibuka ${when(prak.mulai)} jam ${hhmm(prak.mulai)}.`,
          screen: ["Presensi hari ini", `- PV s.d. ${hhmm(pv.selesai)} (QR)`, `- Prak. PV ${hhmm(prak.mulai)}`, "- MSBD sudah diisi"],
          sources: [],
          tools: ["get_attendance"],
          latency_s: 2.4,
        }),
        turn(31 * MIN, {
          question: "Tugas yang deadline-nya paling dekat apa?",
          speech: `Paling dekat ${nextTask.judul} Pemrograman Visual, deadline ${when(nextTask.deadline)} jam ${hhmm(nextTask.deadline)}. Setelah itu latihan normalisasi MSBD, dua hari lagi.`,
          screen: ["Deadline terdekat", `- PV Tugas 5 ${hhmm(nextTask.deadline)}`, "- MSBD normalisasi +2 hr"],
          sources: [],
          tools: ["list_assignments"],
          latency_s: 2.9,
        }),
        turn(6 * MIN, {
          question: "Event handler di Pemrograman Visual itu apa sih?",
          speech: "Event handler adalah method yang dijalankan saat sebuah event terjadi, misalnya tombol diklik. Di Windows Forms, beberapa tombol bisa memakai satu handler yang sama, lalu kamu cek tombol mana yang mengirim lewat parameter sender.",
          screen: ["Event handler", "Method yg jalan saat", "event terjadi (klik).", "1 handler bisa dipakai", "banyak tombol: cek sender"],
          sources: [{ matkul: "Pemrograman Visual", pertemuan: [6], judul: "Event handling dan delegasi" }],
          tools: ["search_materials"],
          latency_s: 3.6,
        }),
      ],
    },
    {
      id: 211,
      started_at: new Date(now - DAY - 3 * HOUR).toISOString(),
      last_active: new Date(now - DAY - 2 * HOUR - 35 * MIN).toISOString(),
      summary: "Membahas normalisasi MSBD pertemuan 6 (1NF sampai 3NF) dan contoh ketergantungan transitif; pengguna masih bingung membedakan 3NF dan BCNF.",
      turns: [
        turn(DAY + 3 * HOUR, {
          question: "Pertemuan 6 MSBD bahas apa?",
          speech: "Pertemuan 6 MSBD membahas normalisasi: 1NF, 2NF, 3NF, dan BCNF, termasuk cara menemukan ketergantungan fungsional dan menghilangkan anomali update.",
          screen: ["MSBD p6: Normalisasi", "- 1NF, 2NF, 3NF, BCNF", "- Ketergantungan fungsi", "- Anomali update"],
          sources: [{ matkul: "Manajemen Sistem Basis Data", pertemuan: [6], judul: "Normalisasi" }],
          tools: ["get_meeting"],
          latency_s: 2.7,
        }),
        turn(DAY + 2 * HOUR + 50 * MIN, {
          question: "Bedanya 3NF sama BCNF apa?",
          speech: "Di 3NF, atribut non-kunci tidak boleh bergantung secara transitif pada kunci. BCNF lebih ketat: setiap penentu harus kunci kandidat. Jadi tabel yang 3NF belum tentu BCNF kalau ada penentu yang bukan kunci kandidat.",
          screen: ["3NF vs BCNF", "3NF: tanpa dependensi", "transitif ke kunci", "BCNF: semua penentu", "harus kunci kandidat"],
          sources: [{ matkul: "Manajemen Sistem Basis Data", pertemuan: [6], judul: "Normalisasi" }],
          tools: ["search_materials"],
          latency_s: 3.9,
        }),
        turn(DAY + 2 * HOUR + 35 * MIN, {
          question: "Kasih contoh ketergantungan transitif",
          speech: "Contohnya tabel Mahasiswa dengan nim, kode prodi, dan nama prodi. Nama prodi bergantung pada kode prodi, dan kode prodi bergantung pada nim. Jadi nama prodi bergantung transitif pada nim.",
          screen: ["Contoh transitif", "nim -> kode_prodi", "kode_prodi -> nama_prodi", "=> nim -> nama_prodi"],
          sources: [{ matkul: "Manajemen Sistem Basis Data", pertemuan: [6], judul: "Normalisasi" }],
          tools: ["search_materials"],
          latency_s: 3.2,
        }),
      ],
    },
    {
      id: 207,
      started_at: new Date(now - 3 * DAY - 10 * HOUR).toISOString(),
      last_active: new Date(now - 3 * DAY - 9 * HOUR - 50 * MIN).toISOString(),
      summary: "Menanyakan jadwal kuliah besok dan ruang praktikum PV.",
      turns: [
        turn(3 * DAY + 10 * HOUR, {
          question: "Jadwal kuliah besok apa aja?",
          speech: "Besok ada Praktikum Pemrograman Visual jam 9 di Laboratorium Komputer, lalu E-Application jam setengah dua di ruang I05.2.1.2.",
          screen: ["Jadwal besok", "- 09.00 Prak. PV Lab Kom", "- 13.30 E-App I05.2.1.2"],
          sources: [],
          tools: [],
          latency_s: 2.1,
        }),
        turn(3 * DAY + 9 * HOUR + 50 * MIN, {
          question: "Praktikum PV minggu ini harus bawa apa?",
          speech: "Di modul praktikum pertemuan 5 kamu diminta menyiapkan Visual Studio dengan template Windows Forms dan proyek dari modul sebelumnya.",
          screen: ["Prak. PV p5", "- Visual Studio siap", "- Template WinForms", "- Proyek modul lalu"],
          sources: [{ matkul: "Praktikum Pemrograman Visual", pertemuan: [5], judul: "Modul 5" }],
          tools: ["get_meeting"],
          latency_s: 3.4,
        }),
      ],
    },
    {
      id: 203,
      started_at: new Date(now - 6 * DAY - 2 * HOUR).toISOString(),
      last_active: new Date(now - 6 * DAY - HOUR - 40 * MIN).toISOString(),
      summary: "Belajar konsep work breakdown structure untuk MPIT.",
      turns: [
        turn(6 * DAY + 2 * HOUR, {
          question: "Apa itu work breakdown structure?",
          speech: "Work breakdown structure atau WBS adalah pemecahan pekerjaan proyek menjadi bagian-bagian kecil yang bisa dikelola, dari deliverable utama sampai paket kerja.",
          screen: ["WBS", "Pecah proyek jadi", "paket kerja kecil", "yang bisa dikelola"],
          sources: [{ matkul: "Manajemen Proyek IT", pertemuan: [3], judul: "Perencanaan lingkup" }],
          tools: ["search_materials"],
          latency_s: 3.1,
        }),
      ],
    },
  ],
};

/* ---------- riwayat belajar ---------- */

const WINDOW = 30;
const todayQuestions = conversations.sessions[0].turns.length;

function buildDaily() {
  const r = rng(41);
  return Array.from({ length: WINDOW }, (_, i) => {
    const ago = WINDOW - 1 - i;
    const day = wib(now - ago * DAY);
    const weekend = day.weekday === "sabtu" || day.weekday === "minggu";
    const questions = ago === 0 ? todayQuestions : r() < (weekend ? 0.35 : 0.75) ? 1 + Math.round(r() * (weekend ? 3 : 7)) : 0;
    return { date: day.date, questions };
  });
}

const daily = buildDaily();

export const learning: LearningData = {
  window_days: WINDOW,
  questions_total: daily.reduce((s, d) => s + d.questions, 0),
  daily,
  courses: [
    { course: "Manajemen Sistem Basis Data", questions: 31, meetings: [4, 5, 6] },
    { course: "Pemrograman Visual", questions: 24, meetings: [3, 5, 6] },
    { course: "Manajemen Proyek IT", questions: 14, meetings: [2, 3] },
    { course: "Praktikum Pemrograman Visual", questions: 9, meetings: [4, 5] },
    { course: "E-Application", questions: 6, meetings: [3] },
    { course: "Praktikum Sistem Pendukung Keputusan", questions: 3, meetings: [4] },
  ],
  sources_top: [
    { course: "Manajemen Sistem Basis Data", pertemuan: 6, judul: "Normalisasi", count: 12 },
    { course: "Pemrograman Visual", pertemuan: 6, judul: "Event handling dan delegasi", count: 8 },
    { course: "Manajemen Sistem Basis Data", pertemuan: 5, judul: "Ketergantungan fungsional", count: 7 },
    { course: "Manajemen Proyek IT", pertemuan: 3, judul: "Perencanaan lingkup", count: 5 },
    { course: "Praktikum Pemrograman Visual", pertemuan: 5, judul: "Modul 5", count: 4 },
  ],
  facts: [
    "Lebih suka penjelasan singkat dengan satu contoh.",
    "Masih bingung membedakan 3NF dan BCNF.",
    "Sering belajar malam hari setelah jam 8.",
    "Sedang menyiapkan UTS Manajemen Sistem Basis Data.",
  ],
};
