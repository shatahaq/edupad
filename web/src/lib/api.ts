// Klien API web EduPad (src/edupad/webapp.py). Cookie sesi HttpOnly dikirim otomatis
// karena halaman dan API satu origin.

export const LOGIN_URL = "/auth/google/login";
export const CONSENT_URL = "/auth/google/login?consent=1";

export type User = {
  name: string | null;
  email: string;
  picture: string | null;
  classroom: {
    granted: boolean;
    reauth_required: boolean;
    courses: number | null;
    synced_at: string | null;
  };
};

export class UnauthorizedError extends Error {
  constructor() {
    super("belum login");
    this.name = "UnauthorizedError";
  }
}

export async function fetchMe(signal?: AbortSignal): Promise<User> {
  const response = await fetch("/api/me", {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
    signal,
  });
  if (response.status === 401) throw new UnauthorizedError();
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return (await response.json()) as User;
}

export async function logout(): Promise<void> {
  const response = await fetch("/auth/logout", { method: "POST", credentials: "same-origin" });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
}

// Kode `?error=` dari server saat login gagal -> pesan untuk pengguna.
const LOGIN_ERRORS: Record<string, string> = {
  access_denied: "Login dibatalkan.",
  state: "Sesi login kedaluwarsa. Silakan coba lagi.",
  not_configured: "Login Google belum dikonfigurasi di server.",
  google_error: "Login dengan Google gagal. Silakan coba lagi.",
};

export function loginErrorMessage(code: string | null): string | null {
  if (!code) return null;
  return LOGIN_ERRORS[code] ?? LOGIN_ERRORS.google_error ?? null;
}
