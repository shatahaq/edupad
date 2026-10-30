import { useEffect, useState } from "react";
import { DATA_SOURCE, LANDING_URL } from "../api/client";

/** Akun Google yang login di web EduPad (GET /api/me milik `edupad serve`). */
export interface Viewer {
  name: string | null;
  email: string;
  picture: string | null;
  classroom: { granted: boolean; reauth_required: boolean; courses: number | null; synced_at: string | null };
}

export const CONSENT_URL = "/auth/google/login?consent=1";

let cached: Promise<Viewer | null> | null = null;

function loadViewer(): Promise<Viewer | null> {
  if (DATA_SOURCE === "mock") return Promise.resolve(null);
  cached ??= fetch("/api/me", { credentials: "include", headers: { Accept: "application/json" } })
    .then((res) => {
      if (res.status === 401) {
        window.location.assign(LANDING_URL);
        return null;
      }
      return res.ok ? (res.json() as Promise<Viewer>) : null;
    })
    .catch(() => null);
  return cached;
}

export function useViewer(): Viewer | null {
  const [viewer, setViewer] = useState<Viewer | null>(null);
  useEffect(() => {
    let alive = true;
    loadViewer().then((value) => alive && setViewer(value));
    return () => {
      alive = false;
    };
  }, []);
  return viewer;
}

/** Keluar lewat web EduPad, lalu kembali ke halaman depan. */
export async function logout() {
  try {
    await fetch("/auth/logout", { method: "POST", credentials: "include" });
  } finally {
    window.location.assign(LANDING_URL);
  }
}
