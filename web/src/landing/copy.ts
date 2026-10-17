// Isi halaman depan dalam dua bahasa. EduPad mendengar & menjawab dalam bahasa Indonesia, jadi
// contoh ucapan versi Inggris tetap ditulis dalam bahasa Indonesia, diberi terjemahan.

export type Lang = "id" | "en";
export type OwlName = "nova" | "pixel" | "sora" | "tempo" | "metric" | "koin" | "nexus";
export type CueName = "listen" | "sent" | "thinking" | "alert" | "error";

/** Ucapan dalam bahasa Indonesia, dengan terjemahan untuk versi Inggris. */
export type Phrase = { said: string; meaning?: string };

/** Statistik bergrafik (UNESCO IESALC 2026); `chart` = deskripsi grafik untuk pembaca layar. */
type Chart = { value: string; label: string; note: string; chart: string; source: string; url: string };

type Copy = {
  skip: string;
  nav: { how: string; owls: string; voice: string; equity: string; label: string };
  signIn: string;
  openDashboard: string;
  langLabel: string;
  loginErrors: Record<string, string>;
  hero: {
    eyebrow: string;
    title: string;
    lead: string;
    listen: string;
    stop: string;
    how: string;
    transcriptLabel: string;
    transcript: string[];
  };
  how: {
    title: string;
    steps: { title: string; body: string }[];
    exampleLabel: string;
    exampleNote: string;
    you: string;
    question: Phrase;
    answerLabel: string;
    answer: Phrase;
    screenLabel: string;
    screen: { title: string; lines: string[] };
  };
  owls: { title: string; lead: string; say: string; list: Record<OwlName, { role: string; body: string; say?: Phrase }> };
  voice: {
    eyebrow: string;
    title: string;
    lead: string;
    turnOn: Phrase;
    listenLabel: string;
    cuesTitle: string;
    cues: Record<CueName, { label: string; body: string }>;
    offlineTitle: string;
    offlineBody: string;
    offlineClip: Phrase;
    more: string[];
  };
  equity: {
    eyebrow: string;
    title: string;
    lead: string;
    points: { title: string; body: string }[];
    messageLabel: string;
    message: string;
    messageNote: string;
  };
  office: { eyebrow: string; title: string; lead: string; alt: string; caption: string };
  behind: {
    title: string;
    lead: string;
    parts: { title: string; body: string }[];
    privacyTitle: string;
    privacy: string[];
    limitsTitle: string;
    limits: string[];
  };
  sdg: {
    eyebrow: string;
    title: string;
    lead: string;
    enrolment: Chart & { before: string; after: string; growth: string };
    graduation: Chart & { from: string; to: string };
    disabilityTitle: string;
    disabilityNote: string;
    stats: { value: string; body: string; source: string; url: string }[];
    fitTitle: string;
    items: { code: string; title: string; body: string }[];
  };
  footer: { tagline: string };
};

export const COPY: Record<Lang, Copy> = {
  id: {
    skip: "Lewati ke isi",
    nav: { how: "Cara kerja", owls: "Fitur", voice: "Mode Suara", equity: "Equity Radar", label: "Navigasi" },
    signIn: "Masuk",
    openDashboard: "Buka dashboard",
    langLabel: "Bahasa",
    loginErrors: {
      access_denied: "Login dibatalkan.",
      state: "Sesi login kedaluwarsa. Silakan coba lagi.",
      not_configured: "Login Google belum dikonfigurasi di server.",
      google_error: "Login dengan Google gagal. Silakan coba lagi.",
    },
    hero: {
      eyebrow: "Asisten belajar berbasis suara",
      title: "Tanya materi kuliah, cukup dengan suara.",
      lead:
        "EduPad adalah perangkat kecil di meja belajar. Ia membaca materi dari dosen, tugas, presensi, dan jadwal kuliah, lalu menjawab pertanyaanmu lewat suara, tanpa perlu membuka aplikasi atau mengetik.",
      listen: "Dengarkan EduPad",
      stop: "Hentikan",
      how: "Lihat cara kerjanya",
      transcriptLabel: "Yang diucapkan EduPad saat menyala",
      transcript: [
        "Halo! Aku EduPad. Teman belajarmu.",
        "Aku bisa menjelaskan materi kuliahmu, mengecek tugas, deadline, dan presensi.",
        "Caranya gampang: tahan tombol, lalu tanya saja. Yuk, mulai belajar!",
      ],
    },
    how: {
      title: "Satu tombol, dari pertanyaan sampai jawaban",
      steps: [
        { title: "Tahan tombol, lalu bertanya", body: "Bicara seperti kepada teman. Tidak ada menu atau aplikasi yang perlu dibuka." },
        {
          title: "EduPad mencari di sumbernya",
          body: "Suaramu diubah jadi teks, lalu AI mencari jawabannya di materi dosen, tugas, dan jadwalmu, bukan menebak.",
        },
        {
          title: "Dijawab lewat suara dan layar",
          body: "Jawaban dibacakan beserta sumber materinya; poin pentingnya tampil di layar kecil.",
        },
        {
          title: "Diingatkan tanpa diminta",
          body: "Presensi yang dibuka, deadline yang mendekat, dan topik yang perlu diulang muncul sendiri.",
        },
      ],
      exampleLabel: "Contoh percakapan",
      exampleNote: "Ilustrasi; isi jawaban selalu diambil dari materi yang benar-benar ada.",
      you: "Kamu",
      question: { said: "Jelaskan bentuk normal ketiga, dong." },
      answerLabel: "EduPad",
      answer: {
        said:
          "Bentuk normal ketiga artinya setiap kolom hanya bergantung pada kunci utama, bukan pada kolom lain. Misalnya kota bergantung pada kode pos, maka kode pos dipisah ke tabelnya sendiri. Ini dari materi Basis Data pertemuan lima.",
      },
      screenLabel: "Di layar",
      screen: {
        title: "3NF",
        lines: ["- Kolom hanya bergantung", "  pada kunci utama", "- Hapus ketergantungan", "  transitif", "- Contoh: kode pos -> kota"],
      },
    },
    owls: {
      title: "Tujuh owl, masing-masing punya tugas",
      lead:
        "Setiap bagian pekerjaan EduPad dipegang satu owl. Di dashboard, owl itu benar-benar bergerak saat pekerjaannya sedang berjalan.",
      say: "Coba ucapkan",
      list: {
        nova: { role: "Koordinator", body: "Menerima pertanyaanmu dan membagikannya ke owl yang tepat." },
        pixel: {
          role: "Materi kuliah",
          body: "Membaca PDF, slide, dan materi Google Classroom, termasuk slide berupa gambar.",
          say: { said: "Pertemuan lima Basis Data bahas apa?" },
        },
        sora: {
          role: "Tutor",
          body: "Menguji pemahaman lewat kuis lisan, dan menyiapkan pelajaran singkat saat sebuah topik terlihat sulit.",
          say: { said: "Uji aku Basis Data pertemuan dua." },
        },
        tempo: {
          role: "Jadwal, tugas, presensi",
          body: "Memberi tahu saat presensi dibuka, mengisinya bila bisa, dan mengingatkan deadline.",
          say: { said: "Tugas apa yang deadline minggu ini?" },
        },
        metric: {
          role: "Progres belajar",
          body: "Mencatat topik yang sudah dikuasai dan yang waktunya diulang.",
          say: { said: "Progres belajarku gimana?" },
        },
        koin: {
          role: "Keuangan",
          body: "Mencatat pengeluaran dari ucapan dan mengingatkan saat anggaran menipis.",
          say: { said: "Tadi beli makan dua puluh lima ribu." },
        },
        nexus: {
          role: "Pengetahuan & Equity Radar",
          body: "Menjaga basis pengetahuan tetap rapi dan menunjukkan materi yang belum tersedia.",
        },
      },
    },
    voice: {
      eyebrow: "Mode Suara",
      title: "Bisa dipakai tanpa melihat layar",
      lead:
        "Dirancang untuk mahasiswa tunanetra. Setelah Mode Suara aktif, seluruh jawaban dan pemberitahuan dibacakan, dan bunyi pendek memberi tahu apa yang sedang terjadi.",
      turnOn: { said: "Aktifkan mode suara." },
      listenLabel: "Dengar",
      cuesTitle: "Bunyi penanda",
      cues: {
        listen: { label: "Mulai merekam", body: "Bunyi naik: silakan bicara." },
        sent: { label: "Rekaman terkirim", body: "Bunyi turun." },
        thinking: { label: "Sedang berpikir", body: "Ketukan pelan setiap dua detik." },
        alert: { label: "Pemberitahuan", body: "Ding-dong, lalu isinya dibacakan." },
        error: { label: "Ada masalah", body: "Dua nada rendah, lalu penjelasannya." },
      },
      offlineTitle: "Tetap bersuara saat offline",
      offlineBody: "Pesan seperti ini disimpan di perangkat, jadi tetap terdengar walau Wi-Fi atau server sedang putus.",
      offlineClip: { said: "Wi-Fi terputus. EduPad sedang mencoba menyambung lagi." },
      more: [
        "Jawaban panjang ditutup dengan “mau dilanjutkan?”; cukup jawab “lanjut”.",
        "Kecepatan bicara bisa diatur: “bicara lebih cepat” atau “bicara lebih lambat”.",
      ],
    },
    equity: {
      eyebrow: "Equity Radar",
      title: "Kesenjangan akses jadi terlihat",
      lead:
        "Tidak semua mahasiswa mendapat materi yang sama lengkapnya. Equity Radar membandingkan pertemuan yang sudah berlangsung dengan materi yang benar-benar tersedia.",
      points: [
        { title: "Pertemuan tanpa materi", body: "Terlihat per mata kuliah, lengkap dengan pesan sopan yang siap dikirim ke dosen." },
        {
          title: "Peringatan dini",
          body: "Jatah tidak hadir yang hampir habis atau anggaran yang menipis diberitahukan sebelum terlambat, bukan sesudahnya.",
        },
        {
          title: "Materi yang bisa didengar",
          body: "Ringkasan tiap pertemuan bisa dibacakan, termasuk slide berupa gambar yang dibaca dengan OCR.",
        },
      ],
      messageLabel: "Contoh pesan ke dosen",
      message:
        "Selamat siang, Bapak/Ibu. Mohon izin, materi pertemuan 6 dan 7 belum tersedia di e-learning maupun Google Classroom. Bila berkenan, mohon materinya dapat diunggah agar bisa kami pelajari ulang. Terima kasih banyak, Bapak/Ibu.",
      messageNote: "Disusun otomatis dari pertemuan yang kosong; tinggal disalin.",
    },
    office: {
      eyebrow: "Dashboard",
      title: "Kantor AI yang bisa dilihat",
      lead:
        "Dashboard menampilkan pekerjaan EduPad sebagai kantor kecil. Saat kamu bertanya soal jadwal, TEMPO yang bergerak; saat kuis, SORA. Ada juga halaman Tutor, Keuangan, dan Equity Radar.",
      alt: "Peta kantor AI Office: tujuh owl di ruangannya masing-masing, sedang bersantai.",
      caption: "Dashboard AI Office saat EduPad sedang menganggur.",
    },
    behind: {
      title: "Di balik layar",
      lead: "Sederhana untuk dipakai, tapi setiap jawaban melewati beberapa langkah.",
      parts: [
        { title: "Perangkat", body: "ESP32-S3 dengan mikrofon, speaker, dan layar 4 inci. Satu tombol untuk semuanya." },
        {
          title: "Server EduPad",
          body: "Suara diubah jadi teks (Whisper), AI menjawab sambil memakai alat pencari materi, tugas, dan jadwal, lalu jawabannya disuarakan (ElevenLabs).",
        },
        {
          title: "Sumber data",
          body: "Materi dan tugas dari e-learning kampus, jadwal dan presensi dari portal akademik, serta Google Classroom.",
        },
        { title: "Dashboard", body: "AI Office, Tutor, Keuangan, dan Equity Radar, di alamat ini." },
      ],
      privacyTitle: "Privasi",
      privacy: [
        "Yang disimpan hanya cookie sesi, bukan password.",
        "Materi dibaca dan di-OCR di server EduPad sendiri.",
        "Dashboard hanya bisa dibuka pemiliknya.",
      ],
      limitsTitle: "Batasan yang kami sadari",
      limits: [
        "Presensi yang wajib scan QR tetap perlu HP.",
        "Jawaban hanya sebaik materi yang tersedia; bila materinya tidak ada, EduPad mengatakannya.",
        "OCR bisa salah baca pada slide yang buram.",
      ],
    },
    sdg: {
      eyebrow: "SDG 4 · SDG 10",
      title: "Akses tumbuh lebih cepat daripada keberhasilan",
      lead:
        "Jumlah mahasiswa di dunia naik lebih dari dua kali lipat, tapi yang lulus hampir tidak bertambah. Pelajar penyandang disabilitas tertinggal paling jauh.",
      enrolment: {
        value: "269 juta",
        label: "mahasiswa di dunia pada 2024",
        note: "Lebih dari dua kali lipat dalam dua dekade.",
        before: "dua dekade lalu",
        after: "2024",
        growth: "> 2×",
        chart: "Grafik batang: jumlah mahasiswa dua dekade lalu kurang dari separuh jumlah 2024 yang mencapai 269 juta.",
        source: "UNESCO IESALC, Higher Education Global Trends Report 2026",
        url: "https://hepo.iesalc.unesco.org/pc/page/content/202606_HEPO_New/",
      },
      graduation: {
        value: "27%",
        label: "rasio kelulusan perguruan tinggi dunia pada 2024",
        note: "Hanya naik 5 poin dari 22% pada 2013.",
        from: "2013",
        to: "2024",
        chart: "Grafik garis: rasio kelulusan dunia 22% pada 2013 dan 27% pada 2024, pada skala 0 sampai 40%.",
        source: "UNESCO IESALC, Higher Education Global Trends Report 2026",
        url: "https://hepo.iesalc.unesco.org/pc/page/content/202606_HEPO_New/",
      },
      disabilityTitle: "Pelajar penyandang disabilitas",
      disabilityNote: "Data usia sekolah, dari 14 negara (2017–2019).",
      stats: [
        {
          value: "+11 poin",
          body: "Anak dengan disabilitas sensorik, fisik, atau intelektual 11 poin persen lebih mungkin tidak bersekolah di usia SMA dibanding teman sebayanya.",
          source: "UNESCO, GEM Report 2020",
          url: "https://gem-report-2020.unesco.org/thematic/",
        },
        {
          value: "Hampir 50%",
          body: "negara berpenghasilan rendah dan menengah tidak mencatat data administratif tentang siswa penyandang disabilitas.",
          source: "UNESCO, GEM Report 2020",
          url: "https://gem-report-2020.unesco.org/thematic/",
        },
      ],
      fitTitle: "Bagian yang dikerjakan EduPad",
      items: [
        {
          code: "SDG 4",
          title: "Pendidikan berkualitas",
          body: "Membantu mahasiswa memahami materi dan menyelesaikan kuliah, bukan sekadar terdaftar: bertanya kapan saja, kuis lisan, dan pengingat sebelum terlambat.",
        },
        {
          code: "SDG 10",
          title: "Berkurangnya kesenjangan",
          body: "Mahasiswa tunanetra bisa memakai semuanya lewat suara, dan kekosongan materi terlihat lebih awal lewat Equity Radar.",
        },
      ],
    },
    footer: { tagline: "Asisten belajar berbasis suara." },
  },

  en: {
    skip: "Skip to content",
    nav: { how: "How it works", owls: "Features", voice: "Voice Mode", equity: "Equity Radar", label: "Navigation" },
    signIn: "Sign in",
    openDashboard: "Open dashboard",
    langLabel: "Language",
    loginErrors: {
      access_denied: "Sign-in was cancelled.",
      state: "The sign-in session expired. Please try again.",
      not_configured: "Google sign-in is not set up on the server yet.",
      google_error: "Signing in with Google failed. Please try again.",
    },
    hero: {
      eyebrow: "A voice-first study assistant",
      title: "Ask about your lectures. Just say it.",
      lead:
        "EduPad is a small device that sits on your desk. It reads your lecturers' materials, assignments, attendance and class schedule, then answers your questions out loud, with no app to open and nothing to type.",
      listen: "Listen to EduPad",
      stop: "Stop",
      how: "See how it works",
      transcriptLabel: "What EduPad says when it starts (in Indonesian)",
      transcript: [
        "Hi! I'm EduPad, your study buddy.",
        "I can explain your course materials, and check assignments, deadlines and attendance.",
        "It's easy: hold the button and just ask. Let's start studying!",
      ],
    },
    how: {
      title: "One button, from question to answer",
      steps: [
        { title: "Hold the button and ask", body: "Talk the way you would to a friend. No menus, no app to open." },
        {
          title: "EduPad looks it up",
          body: "Your voice becomes text, then the AI finds the answer in your lecturers' materials, assignments and schedule instead of guessing.",
        },
        {
          title: "Answered by voice and on screen",
          body: "The answer is read aloud with its source; the key points appear on the small screen.",
        },
        {
          title: "Reminded without asking",
          body: "Open attendance, upcoming deadlines and topics due for review show up on their own.",
        },
      ],
      exampleLabel: "Example conversation",
      exampleNote: "Illustrative. EduPad speaks Indonesian, and its answers always come from materials that actually exist.",
      you: "You",
      question: { said: "Jelaskan bentuk normal ketiga, dong.", meaning: "Can you explain third normal form?" },
      answerLabel: "EduPad",
      answer: {
        said:
          "Bentuk normal ketiga artinya setiap kolom hanya bergantung pada kunci utama, bukan pada kolom lain. Misalnya kota bergantung pada kode pos, maka kode pos dipisah ke tabelnya sendiri. Ini dari materi Basis Data pertemuan lima.",
        meaning:
          "Third normal form means every column depends only on the primary key, not on another column. If the city depends on the postcode, move the postcode into its own table. This is from Databases, meeting five.",
      },
      screenLabel: "On screen",
      screen: {
        title: "3NF",
        lines: ["- Kolom hanya bergantung", "  pada kunci utama", "- Hapus ketergantungan", "  transitif", "- Contoh: kode pos -> kota"],
      },
    },
    owls: {
      title: "Seven owls, each with a job",
      lead: "Each part of EduPad's work belongs to one owl. On the dashboard, that owl actually moves while its job is running.",
      say: "Try saying",
      list: {
        nova: { role: "Coordinator", body: "Takes your question and hands it to the right owl." },
        pixel: {
          role: "Course materials",
          body: "Reads PDFs, slides and Google Classroom materials, including slides that are only images.",
          say: { said: "Pertemuan lima Basis Data bahas apa?", meaning: "What does Databases, meeting five, cover?" },
        },
        sora: {
          role: "Tutor",
          body: "Checks understanding with spoken quizzes, and prepares a short lesson when a topic looks hard.",
          say: { said: "Uji aku Basis Data pertemuan dua.", meaning: "Quiz me on Databases, meeting two." },
        },
        tempo: {
          role: "Schedule, assignments, attendance",
          body: "Tells you when attendance opens, fills it in when it can, and reminds you of deadlines.",
          say: { said: "Tugas apa yang deadline minggu ini?", meaning: "Which assignments are due this week?" },
        },
        metric: {
          role: "Learning progress",
          body: "Keeps track of the topics you have mastered and the ones due for review.",
          say: { said: "Progres belajarku gimana?", meaning: "How is my progress?" },
        },
        koin: {
          role: "Money",
          body: "Records spending from what you say and warns you when a budget runs low.",
          say: { said: "Tadi beli makan dua puluh lima ribu.", meaning: "I just spent twenty-five thousand on food." },
        },
        nexus: {
          role: "Knowledge & Equity Radar",
          body: "Keeps the knowledge base in order and shows which materials are still missing.",
        },
      },
    },
    voice: {
      eyebrow: "Voice Mode",
      title: "Usable without looking at the screen",
      lead:
        "Designed for blind students. Once Voice Mode is on, every answer and notification is read aloud, and short sounds tell you what is happening.",
      turnOn: { said: "Aktifkan mode suara.", meaning: "Turn on voice mode." },
      listenLabel: "Listen",
      cuesTitle: "Sound cues",
      cues: {
        listen: { label: "Recording starts", body: "A rising tone: go ahead and speak." },
        sent: { label: "Recording sent", body: "A falling tone." },
        thinking: { label: "Thinking", body: "A soft tick every two seconds." },
        alert: { label: "Notification", body: "A ding-dong, then it is read aloud." },
        error: { label: "Something went wrong", body: "Two low tones, then an explanation." },
      },
      offlineTitle: "Still talks when offline",
      offlineBody: "Messages like this one are stored on the device, so you hear them even when Wi-Fi or the server is down.",
      offlineClip: {
        said: "Wi-Fi terputus. EduPad sedang mencoba menyambung lagi.",
        meaning: "Wi-Fi disconnected. EduPad is trying to reconnect.",
      },
      more: [
        "Long answers end with “mau dilanjutkan?” (shall I continue?); just say “lanjut”.",
        "Speaking speed can be changed: “bicara lebih cepat” (speak faster) or “bicara lebih lambat” (speak slower).",
      ],
    },
    equity: {
      eyebrow: "Equity Radar",
      title: "Gaps in access become visible",
      lead:
        "Not every student gets equally complete materials. Equity Radar compares the meetings that have already happened with the materials that actually exist.",
      points: [
        { title: "Meetings without materials", body: "Shown per course, with a polite message ready to send to the lecturer." },
        {
          title: "Early warnings",
          body: "An absence allowance that is almost used up, or a budget that is running low, is flagged before it is too late, not after.",
        },
        {
          title: "Materials you can listen to",
          body: "Every meeting's summary can be read aloud, including slides that are only images, read with OCR.",
        },
      ],
      messageLabel: "Example message to a lecturer (in Indonesian)",
      message:
        "Selamat siang, Bapak/Ibu. Mohon izin, materi pertemuan 6 dan 7 belum tersedia di e-learning maupun Google Classroom. Bila berkenan, mohon materinya dapat diunggah agar bisa kami pelajari ulang. Terima kasih banyak, Bapak/Ibu.",
      messageNote:
        "Written automatically from the empty meetings, ready to copy. It politely asks for the missing materials of meetings 6 and 7.",
    },
    office: {
      eyebrow: "Dashboard",
      title: "An AI office you can watch",
      lead:
        "The dashboard shows EduPad's work as a small office. Ask about your schedule and TEMPO gets moving; start a quiz and SORA does. There are also pages for the Tutor, money and the Equity Radar.",
      alt: "Map of the AI Office: seven owls in their rooms, taking a break.",
      caption: "The AI Office dashboard while EduPad is idle.",
    },
    behind: {
      title: "Behind the scenes",
      lead: "Simple to use, but every answer goes through a few steps.",
      parts: [
        { title: "Device", body: "An ESP32-S3 with a microphone, a speaker and a 4-inch screen. One button for everything." },
        {
          title: "EduPad server",
          body: "Speech becomes text (Whisper), the AI answers using tools that search materials, assignments and the schedule, and the answer is voiced (ElevenLabs).",
        },
        {
          title: "Data sources",
          body: "Materials and assignments from the campus e-learning site, schedule and attendance from the academic portal, and Google Classroom.",
        },
        { title: "Dashboard", body: "AI Office, Tutor, money and Equity Radar, right here." },
      ],
      privacyTitle: "Privacy",
      privacy: [
        "Only session cookies are stored, never passwords.",
        "Materials are read and OCR'd on EduPad's own server.",
        "Only the owner can open the dashboard.",
      ],
      limitsTitle: "Limits we know about",
      limits: [
        "Attendance that requires scanning a QR code still needs a phone.",
        "Answers are only as good as the available materials; when something is missing, EduPad says so.",
        "OCR can misread blurry slides.",
      ],
    },
    sdg: {
      eyebrow: "SDG 4 · SDG 10",
      title: "Access is growing faster than success",
      lead:
        "The number of university students has more than doubled, yet the share who graduate has barely moved. Learners with disabilities are left furthest behind.",
      enrolment: {
        value: "269 million",
        label: "university students worldwide in 2024",
        note: "More than double in two decades.",
        before: "two decades ago",
        after: "2024",
        growth: "> 2×",
        chart: "Bar chart: student numbers two decades ago were less than half of the 269 million reached in 2024.",
        source: "UNESCO IESALC, Higher Education Global Trends Report 2026",
        url: "https://hepo.iesalc.unesco.org/pc/page/content/202606_HEPO_New/",
      },
      graduation: {
        value: "27%",
        label: "global higher-education graduation ratio in 2024",
        note: "Up only 5 points from 22% in 2013.",
        from: "2013",
        to: "2024",
        chart: "Line chart: the global graduation ratio was 22% in 2013 and 27% in 2024, on a scale from 0 to 40%.",
        source: "UNESCO IESALC, Higher Education Global Trends Report 2026",
        url: "https://hepo.iesalc.unesco.org/pc/page/content/202606_HEPO_New/",
      },
      disabilityTitle: "Learners with disabilities",
      disabilityNote: "School-age data from 14 countries (2017–2019).",
      stats: [
        {
          value: "+11 points",
          body: "Children with a sensory, physical or intellectual disability are 11 percentage points more likely to be out of school at upper-secondary age than their peers.",
          source: "UNESCO, GEM Report 2020",
          url: "https://gem-report-2020.unesco.org/thematic/",
        },
        {
          value: "Almost 50%",
          body: "of low- and middle-income countries collect no administrative data on students with disabilities.",
          source: "UNESCO, GEM Report 2020",
          url: "https://gem-report-2020.unesco.org/thematic/",
        },
      ],
      fitTitle: "Where EduPad helps",
      items: [
        {
          code: "SDG 4",
          title: "Quality education",
          body: "Helps students understand their courses and finish them, not just enrol: ask any time, spoken quizzes, and reminders before it is too late.",
        },
        {
          code: "SDG 10",
          title: "Reduced inequalities",
          body: "Blind students can use everything by voice, and missing materials show up early through the Equity Radar.",
        },
      ],
    },
    footer: { tagline: "A voice-first study assistant." },
  },
};
