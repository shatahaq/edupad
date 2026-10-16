/**
 * DATA DUMMY. Hanya dipakai saat VITE_DATA_SOURCE=mock.
 *
 * Angka di sini karangan, tetapi bentuknya wajib sama persis dengan types.ts (dicek
 * TypeScript lewat `satisfies`). Saat endpoint server sudah ada, folder ini boleh dibiarkan
 * untuk demo/pengembangan UI atau dihapus seluruhnya tanpa mengubah komponen.
 * Angka acak memakai seed tetap sehingga tampilan sama setiap dimuat.
 */
import type { DashboardData, PanelKey } from "../types";
import { equity, finance, tutor } from "./learning";
import { assignments, attendance, conversations, learning, schedule } from "./student";

function rng(seed: number) {
  return () => {
    seed = (seed * 1664525 + 1013904223) % 2 ** 32;
    return seed / 2 ** 32;
  };
}

const HOUR = 3600_000;
const now = Date.now();
/** Awal jam berjalan, untuk deret per jam. */
const hourNow = Math.floor(now / HOUR) * HOUR;
const iso = (msAgo: number) => new Date(now - msAgo).toISOString();
const hourIso = (hoursAgo: number) => new Date(hourNow - hoursAgo * HOUR).toISOString();
const round = (n: number, d = 2) => Math.round(n * 10 ** d) / 10 ** d;

/** Pola pemakaian mahasiswa: ramai jam kuliah & malam, sepi dini hari. Jam = WIB. */
function traffic(hour: number) {
  if (hour < 6) return 0.05;
  if (hour < 8) return 0.35;
  if (hour < 12) return 1;
  if (hour < 13) return 0.5;
  if (hour < 17) return 0.8;
  if (hour < 19) return 0.4;
  if (hour < 23) return 0.9;
  return 0.25;
}

function wibHour(hoursAgo: number) {
  return (new Date(hourNow - hoursAgo * HOUR).getUTCHours() + 7) % 24;
}

function buildApiSeries() {
  const r = rng(7);
  return Array.from({ length: 24 }, (_, i) => {
    const ago = 23 - i;
    const requests = Math.round(traffic(wibHour(ago)) * (14 + r() * 8));
    return {
      time: hourIso(ago),
      requests,
      errors: requests > 4 && r() < 0.25 ? 1 : 0,
      latency_avg_s: round(2.6 + r() * 0.9 + (requests > 15 ? 0.4 : 0)),
    };
  });
}

const apiSeries = buildApiSeries();
const apiRequests = apiSeries.reduce((s, p) => s + p.requests, 0);
const apiErrors = apiSeries.reduce((s, p) => s + p.errors, 0);

function buildDaily() {
  const r = rng(11);
  const today = new Date(now);
  return Array.from({ length: today.getUTCDate() }, (_, i) => {
    const d = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), i + 1));
    const weekend = d.getUTCDay() === 0 || d.getUTCDay() === 6;
    return { date: d.toISOString().slice(0, 10), usd: round((weekend ? 0.03 : 0.09) + r() * 0.06, 3) };
  });
}

const daily = buildDaily();
const monthTotal = round(daily.reduce((s, d) => s + d.usd, 0));
const daysInMonth = new Date(new Date(now).getUTCFullYear(), new Date(now).getUTCMonth() + 1, 0).getDate();

function buildActivity() {
  const r = rng(23);
  return Array.from({ length: 7 }, (_, day) =>
    Array.from({ length: 24 }, (_, hour) => {
      const weekend = day >= 5 ? 0.35 : 1;
      return Math.round(traffic(hour) * weekend * (6 + r() * 5));
    }),
  );
}

function buildErrorHours() {
  const r = rng(31);
  return Array.from({ length: 24 }, (_, i) => {
    const ago = 23 - i;
    const h = wibHour(ago);
    return { time: hourIso(ago), count: r() < traffic(h) * 0.35 ? 1 + Math.round(r() * (h === 8 ? 3 : 1)) : 0 };
  });
}

const DATA = {
  devices: {
    devices: [
      { id: "edupad-01", name: "EduPad Shata", online: true, last_seen: iso(40_000), battery_pct: 82, rssi_dbm: -54, avg_latency_s: 3.1 },
      { id: "edupad-02", name: "EduPad Lab", online: true, last_seen: iso(3 * 60_000), battery_pct: null, rssi_dbm: -67, avg_latency_s: 3.6 },
      { id: "edupad-03", name: "EduPad Uji", online: false, last_seen: iso(26 * HOUR), battery_pct: 12, rssi_dbm: null, avg_latency_s: null },
    ],
  },
  api: {
    window_hours: 24,
    requests: apiRequests,
    by_status: {
      ok: apiRequests - apiErrors - 9,
      no_speech: 9,
      client_error: Math.min(1, apiErrors),
      server_error: Math.max(0, apiErrors - 1),
    },
    latency_avg_s: 3.0,
    latency_p95_s: 5.1,
    latency_goal_s: 3.5,
    series: apiSeries,
  },
  agent: {
    window_hours: 24,
    answers: apiRequests - apiErrors - 9,
    stage_avg_s: { stt: 0.42, agent: 2.58, tts_first_audio: 0.95 },
    tokens_avg: 3840,
    llm_calls_avg: 2.1,
    with_source_pct: 91,
    eval: { label: "v5-riwayat-tool", score: 4.96, max_score: 5, hallucinations: 0, cases: 20 },
    tools: [
      { tool: "search_materials", count: 118 },
      { tool: "get_meeting", count: 74 },
      { tool: "list_assignments", count: 41 },
      { tool: "remember", count: 6 },
    ],
    top_courses: [
      { course: "Pemrograman Visual", questions: 52 },
      { course: "Manajemen Sistem Basis Data", questions: 39 },
      { course: "Manajemen Proyek IT", questions: 24 },
      { course: "E-Application", questions: 17 },
      { course: "Prak. Pemrograman Visual", questions: 11 },
    ],
  },
  services: {
    services: [
      { id: "groq", name: "Groq", role: "Speech-to-text", state: "ok", avg_latency_s: 0.42, errors_24h: 0, quota: null },
      { id: "deepseek", name: "DeepSeek", role: "LLM agent", state: "ok", avg_latency_s: 2.4, errors_24h: 1, quota: null },
      { id: "elevenlabs", name: "ElevenLabs", role: "Text-to-speech", state: "ok", avg_latency_s: 0.95, errors_24h: 0, quota: { used: 7240, limit: 10000, unit: "karakter" } },
      { id: "supabase", name: "Supabase", role: "Memory & vektor", state: "ok", avg_latency_s: 0.12, errors_24h: 0, quota: null },
      { id: "cloudflare", name: "Cloudflare AI", role: "Embedding & rerank", state: "slow", avg_latency_s: 1.3, errors_24h: 2, quota: null },
      { id: "moodle", name: "kelas.usu.ac.id", role: "Sumber materi", state: "ok", avg_latency_s: 1.8, errors_24h: 0, quota: null },
      { id: "satu", name: "Portal SATU", role: "Jadwal & presensi", state: "down", avg_latency_s: null, errors_24h: 3, quota: null },
    ],
  },
  resources: {
    cpu_pct: 23,
    memory_pct: 61,
    disk_pct: 38,
    memory_used_mb: 1250,
    memory_total_mb: 2048,
    active_sessions: 2,
    uptime_s: 4 * 86400 + 6 * 3600,
  },
  knowledge: {
    chunks_total: 1874,
    courses_total: 6,
    last_pipeline_at: iso(75 * 60_000),
    last_pipeline_ok: true,
    new_materials_24h: 3,
    pending_index: 12,
    per_course: [
      { course: "Manajemen Sistem Basis Data", chunks: 512, meetings: 4 },
      { course: "Pemrograman Visual", chunks: 438, meetings: 5 },
      { course: "Praktikum Pemrograman Visual", chunks: 361, meetings: 6 },
      { course: "Manajemen Proyek IT", chunks: 287, meetings: 3 },
      { course: "E-Application", chunks: 176, meetings: 3 },
      { course: "Praktikum Sistem Pendukung Keputusan", chunks: 100, meetings: 1 },
    ],
  },
  errors: {
    by_hour: buildErrorHours(),
    top: [
      { kind: "Portal SATU: sesi berakhir", count: 3, last_at: iso(2 * HOUR) },
      { kind: "Cloudflare AI: timeout embed", count: 2, last_at: iso(5 * HOUR) },
      { kind: "DeepSeek: 502 Bad Gateway", count: 1, last_at: iso(9 * HOUR) },
      { kind: "Rekaman > 120 detik (413)", count: 1, last_at: iso(14 * HOUR) },
    ],
  },
  cost: {
    month: new Date(now).toISOString().slice(0, 7),
    total_usd: monthTotal,
    budget_month_usd: 5,
    forecast_usd: round((monthTotal / daily.length) * daysInMonth),
    by_service: [
      { service: "DeepSeek", usd: round(monthTotal * 0.92) },
      { service: "Cloudflare AI", usd: round(monthTotal * 0.08) },
      { service: "Groq", usd: 0 },
      { service: "ElevenLabs", usd: 0 },
      { service: "Supabase", usd: 0 },
    ],
    daily,
  },
  activity: {
    matrix: buildActivity(),
    top_questions: [
      { text: "Tugas apa saja minggu ini?", count: 31 },
      { text: "Pertemuan N <matkul> bahas apa?", count: 24 },
      { text: "Jelaskan materi <topik>", count: 19 },
      { text: "Jadwal kuliah besok", count: 12 },
      { text: "Deadline tugas <matkul>", count: 9 },
    ],
  },
  attendance,
  assignments,
  schedule,
  conversations,
  learning,
  tutor,
  equity,
  finance,
} satisfies DashboardData;

export async function mockPanel<K extends PanelKey>(panel: K): Promise<DashboardData[K]> {
  // Jeda kecil agar status loading ikut teruji seperti di jaringan asli.
  await new Promise((r) => setTimeout(r, 150 + Math.random() * 250));
  return DATA[panel] as DashboardData[K];
}
