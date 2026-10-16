/**
 * Kontrak data dashboard.
 *
 * Satu tipe = satu panel = satu endpoint GET di server (lihat ENDPOINTS di client.ts).
 * Data dummy (mock/) dan server asli wajib mengembalikan bentuk yang sama, jadi komponen
 * tidak pernah tahu sumber datanya. Field yang belum bisa diukur perangkat/server dibuat
 * `| null` dan ditampilkan "—", bukan diisi angka karangan.
 *
 * Waktu selalu ISO 8601 (UTC), durasi dalam detik, biaya dalam USD.
 */

export interface Device {
  id: string;
  name: string;
  online: boolean;
  last_seen: string;
  /** Firmware belum mengirim; null sampai ada. */
  battery_pct: number | null;
  /** Kekuatan Wi-Fi (dBm); null sampai firmware mengirim. */
  rssi_dbm: number | null;
  /** Rata-rata waktu permintaan /v1/ask terakhir, detik. */
  avg_latency_s: number | null;
}

export interface DevicesData {
  devices: Device[];
}

export type AskStatus = "ok" | "no_speech" | "client_error" | "server_error";

export interface ApiHealthData {
  window_hours: number;
  requests: number;
  by_status: Record<AskStatus, number>;
  /** Akhir bicara -> layar (stt + agent), detik. */
  latency_avg_s: number;
  latency_p95_s: number;
  latency_goal_s: number;
  /** Per jam, urut waktu naik. */
  series: { time: string; requests: number; errors: number; latency_avg_s: number }[];
}

export interface AgentData {
  window_hours: number;
  answers: number;
  /** Rata-rata per tahap; dari `timing` /v1/ask dan TTS. */
  stage_avg_s: { stt: number | null; agent: number | null; tts_first_audio: number | null };
  tokens_avg: number;
  llm_calls_avg: number;
  /** Persen jawaban yang memakai minimal satu sumber materi. */
  with_source_pct: number | null;
  /** Dari `python -m edupad eval` terakhir (bukan real-time). */
  eval: { label: string; score: number; max_score: number; hallucinations: number; cases: number } | null;
  tools: { tool: string; count: number }[];
  top_courses: { course: string; questions: number }[];
}

export type ServiceState = "ok" | "slow" | "down" | "unknown";

export interface ServiceStatus {
  id: string;
  name: string;
  role: string;
  state: ServiceState;
  avg_latency_s: number | null;
  errors_24h: number;
  /** Kuota bulanan, bila layanan punya batas (mis. karakter ElevenLabs). */
  quota: { used: number; limit: number; unit: string } | null;
}

export interface ServicesData {
  services: ServiceStatus[];
}

export interface ResourcesData {
  cpu_pct: number | null;
  memory_pct: number | null;
  disk_pct: number | null;
  memory_used_mb: number | null;
  memory_total_mb: number | null;
  active_sessions: number;
  uptime_s: number;
}

export interface KnowledgeData {
  chunks_total: number;
  courses_total: number;
  last_pipeline_at: string | null;
  last_pipeline_ok: boolean | null;
  new_materials_24h: number;
  /** Chunk yang ada di corpus tetapi belum di-embed ke Supabase. */
  pending_index: number;
  per_course: { course: string; chunks: number; meetings: number }[];
}

export interface ErrorsData {
  /** 24 titik, satu per jam, urut waktu naik. */
  by_hour: { time: string; count: number }[];
  top: { kind: string; count: number; last_at: string }[];
}

export interface CostData {
  month: string;
  total_usd: number;
  budget_month_usd: number | null;
  forecast_usd: number;
  by_service: { service: string; usd: number }[];
  /** Biaya per hari bulan ini, urut tanggal naik. */
  daily: { date: string; usd: number }[];
}

export interface ActivityData {
  /** matrix[hari][jam]; hari 0 = Senin, jam 0..23 waktu lokal server (WIB). */
  matrix: number[][];
  top_questions: { text: string; count: number }[];
}

/* ---------- data mahasiswa (yang ditanyakan ke perangkat) ---------- */

/**
 * Jendela presensi saat ini, dihitung server dengan logika `presence_window()`
 * (src/edupad/agent/tools.py) agar dashboard dan agent selalu sepakat.
 */
export type PresenceWindow = "sudah_diisi" | "dibuka" | "belum_dibuka" | "tutup" | "belum_dijadwalkan";

export interface AttendanceMeeting {
  /** id pertemuan di portal SATU. */
  id: string;
  course: string;
  kode: string;
  kelas: string;
  pertemuan: number;
  topik: string | null;
  /** Jendela presensi; null bila belum dijadwalkan. */
  mulai: string | null;
  selesai: string | null;
  status: "hadir" | null;
  window: PresenceWindow;
  cara: ("QR" | "langsung")[];
}

export interface AttendanceData {
  /** `diperbarui` di data/schedule/attendance.json. */
  updated_at: string | null;
  /** true bila data lebih dari 3 jam lalu (STALE_AFTER di tools.py). */
  stale: boolean;
  today: AttendanceMeeting[];
  /** 7 hari ke depan, tanpa hari ini; urut waktu naik. */
  upcoming: AttendanceMeeting[];
  recap: { course: string; kode: string; kelas: string; hadir: number; pertemuan: number }[];
}

export interface Task {
  /** cmid Moodle. */
  id: string;
  /** Nama bersih, tanpa "[kode]" dan "- Kelas". */
  course: string;
  kode: string;
  jenis: "tugas" | "kuis";
  judul: string;
  pertemuan: number | null;
  dibuka: string | null;
  /** null = tanpa batas waktu. */
  deadline: string | null;
  submitted: boolean;
  late_submission: boolean;
  overdue: boolean;
  graded: boolean;
  nilai: string | null;
  url: string;
  /** Cuplikan soal (maks ~600 karakter, seperti list_assignments). */
  soal: string;
}

export interface AssignmentsData {
  updated_at: string | null;
  tasks: Task[];
}

export type Weekday = "senin" | "selasa" | "rabu" | "kamis" | "jumat" | "sabtu" | "minggu";

export interface ClassSlot {
  hari: Weekday;
  /** "HH:MM" WIB. */
  mulai: string;
  selesai: string;
  kode: string;
  course: string;
  jenis: "teori" | "praktikum";
  kelas: string;
  sks: number;
  ruang: string;
  nama_ruang: string;
  dosen: string[];
}

export interface ScheduleData {
  updated_at: string | null;
  classes: ClassSlot[];
}

export interface TurnSource {
  matkul: string;
  pertemuan: number[];
  judul: string | null;
}

export interface ConversationTurn {
  id: number;
  at: string;
  question: string;
  /** Jawaban yang disuarakan. */
  speech: string;
  /** Baris layar LCD perangkat. */
  screen: string[];
  sources: TurnSource[];
  tools: string[];
  /** stt + agent, detik; null bila tidak tercatat. */
  latency_s: number | null;
}

export interface ConversationSession {
  id: number;
  started_at: string;
  last_active: string;
  /** Ringkasan otomatis memory (agent_sessions.summary). */
  summary: string | null;
  turns: ConversationTurn[];
}

export interface ConversationsData {
  /** Sesi terbaru dulu. */
  sessions: ConversationSession[];
}

export interface LearningData {
  window_days: number;
  questions_total: number;
  /** Satu titik per hari, urut tanggal naik (YYYY-MM-DD, WIB). */
  daily: { date: string; questions: number }[];
  courses: { course: string; questions: number; meetings: number[] }[];
  /** Materi yang paling sering dirujuk jawaban agent. */
  sources_top: { course: string; pertemuan: number; judul: string | null; count: number }[];
  /** Fakta yang diingat agent tentang pengguna (agent_memories). */
  facts: string[];
}

/** Semua panel, dipakai client & mock agar nama endpoint selalu cocok. */
export interface DashboardData {
  devices: DevicesData;
  api: ApiHealthData;
  agent: AgentData;
  services: ServicesData;
  resources: ResourcesData;
  knowledge: KnowledgeData;
  errors: ErrorsData;
  cost: CostData;
  activity: ActivityData;
  attendance: AttendanceData;
  assignments: AssignmentsData;
  schedule: ScheduleData;
  conversations: ConversationsData;
  learning: LearningData;
}

export type PanelKey = keyof DashboardData;
