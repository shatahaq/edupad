/**
 * Satu-satunya pintu data untuk komponen.
 *
 * VITE_DATA_SOURCE=mock -> data dummy (src/api/mock/), dimuat dengan import dinamis sehingga
 *                          tidak ikut ter-bundle di build live.
 * VITE_DATA_SOURCE=live -> GET {VITE_API_URL}{ENDPOINTS[panel]} dengan token Bearer.
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
};

export const DATA_SOURCE: "mock" | "live" =
  import.meta.env.VITE_DATA_SOURCE === "live" ? "live" : "mock";

export const REFRESH_SECONDS = Number(import.meta.env.VITE_REFRESH_SECONDS) || 30;

const API_URL = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");
const API_TOKEN = import.meta.env.VITE_API_TOKEN ?? "";

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
    headers: API_TOKEN ? { Authorization: `Bearer ${API_TOKEN}` } : undefined,
  });
  if (!res.ok) throw new ApiError(`HTTP ${res.status} dari ${ENDPOINTS[panel]}`, res.status);
  return (await res.json()) as DashboardData[K];
}

async function fetchMock<K extends PanelKey>(panel: K): Promise<DashboardData[K]> {
  const { mockPanel } = await import("./mock");
  return mockPanel(panel);
}

export function fetchPanel<K extends PanelKey>(panel: K, signal?: AbortSignal): Promise<DashboardData[K]> {
  return DATA_SOURCE === "live" ? fetchLive(panel, signal) : fetchMock(panel);
}
