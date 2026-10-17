/**
 * Satu-satunya pintu data untuk komponen.
 *
 * VITE_DATA_SOURCE=mock -> data dummy (src/api/mock/), dimuat dengan import dinamis sehingga
 *                          tidak ikut ter-bundle di build live.
 * VITE_DATA_SOURCE=live -> GET {VITE_API_URL}{ENDPOINTS[panel]}.
 *
 * Menyambungkan ke server = implementasikan endpoint di ENDPOINTS dengan bentuk JSON sesuai
 * types.ts. Tidak ada komponen yang perlu diubah.
 */
import type { DashboardData, PanelKey } from "./types";

export const ENDPOINTS: Record<PanelKey, string> = {
  devices: "/v1/dashboard/devices",
  api: "/v1/dashboard/api",
  agent: "/v1/dashboard/agent",
  services: "/v1/dashboard/services",
  resources: "/v1/dashboard/resources",
  knowledge: "/v1/dashboard/knowledge",
  errors: "/v1/dashboard/errors",
  cost: "/v1/dashboard/cost",
  activity: "/v1/dashboard/activity",
  attendance: "/v1/dashboard/attendance",
  assignments: "/v1/dashboard/assignments",
  schedule: "/v1/dashboard/schedule",
  conversations: "/v1/dashboard/conversations",
  learning: "/v1/dashboard/learning",
  tutor: "/v1/dashboard/tutor",
  equity: "/v1/dashboard/equity",
  finance: "/v1/dashboard/finance",
  voice: "/v1/dashboard/voice",
};

/** Halaman depan web EduPad (login Google); dashboard kembali ke sini bila sesi habis. */
export const LANDING_URL = import.meta.env.VITE_LANDING_URL ?? "/";

function toLanding() {
  if (DATA_SOURCE === "live") window.location.assign(LANDING_URL);
}

export const DATA_SOURCE: "mock" | "live" =
  import.meta.env.VITE_DATA_SOURCE === "mock" ? "mock" : "live";

export const REFRESH_SECONDS = Number(import.meta.env.VITE_REFRESH_SECONDS) || 30;

export const API_URL = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
  }
}

async function fetchLive<K extends PanelKey>(panel: K, signal?: AbortSignal): Promise<DashboardData[K]> {
  const res = await fetch(API_URL + ENDPOINTS[panel], {
    signal,
    credentials: "include",
  });
  if (res.status === 401) toLanding();
  if (!res.ok) throw new ApiError(`HTTP ${res.status} dari ${ENDPOINTS[panel]}`, res.status);
  return (await res.json()) as DashboardData[K];
}

/** Penulisan ke Office API (keuangan). Error berisi pesan `detail` dari server. */
export async function apiSend<T = unknown>(method: "POST" | "PUT" | "DELETE", path: string, body?: unknown): Promise<T> {
  const res = await fetch(API_URL + path, {
    method,
    credentials: "include",
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (res.status === 401) toLanding();
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      if (typeof data?.detail === "string") detail = data.detail;
      else if (Array.isArray(data?.detail)) detail = data.detail.map((d: { msg?: string }) => d.msg).join(", ");
    } catch {
      // badan bukan JSON
    }
    throw new ApiError(detail, res.status);
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}

async function fetchMock<K extends PanelKey>(panel: K): Promise<DashboardData[K]> {
  const { mockPanel } = await import("./mock");
  return mockPanel(panel);
}

export function fetchPanel<K extends PanelKey>(panel: K, signal?: AbortSignal): Promise<DashboardData[K]> {
  return DATA_SOURCE === "live" ? fetchLive(panel, signal) : fetchMock(panel);
}
