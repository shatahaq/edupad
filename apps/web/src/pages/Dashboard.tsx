import { useCallback, useEffect, useState } from "react";

import { Wordmark } from "../components/Wordmark";
import { CONSENT_URL, UnauthorizedError, fetchMe, logout, type User } from "../lib/api";
import { navigate } from "../lib/router";

type State =
  | { kind: "loading" }
  | { kind: "error" }
  | { kind: "ready"; user: User };

export default function Dashboard() {
  const [state, setState] = useState<State>({ kind: "loading" });
  const [loggingOut, setLoggingOut] = useState(false);

  const load = useCallback((signal?: AbortSignal) => {
    setState({ kind: "loading" });
    fetchMe(signal)
      .then((user) => setState({ kind: "ready", user }))
      .catch((error: unknown) => {
        if (signal?.aborted) return;
        if (error instanceof UnauthorizedError) navigate("/", { replace: true });
        else setState({ kind: "error" });
      });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  async function handleLogout() {
    setLoggingOut(true);
    try {
      await logout();
    } catch {
      // Server tidak terjangkau: halaman depan akan memeriksa ulang sesi.
    }
    navigate("/", { replace: true });
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="flex items-center justify-between px-4 py-4 sm:px-8">
        <span className="text-2xl">
          <Wordmark />
        </span>
        {state.kind === "ready" && (
          <button
            type="button"
            onClick={handleLogout}
            disabled={loggingOut}
            className="rounded-full px-4 py-2 text-sm font-semibold text-stone-700 transition hover:bg-stone-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 disabled:opacity-60 dark:text-stone-300 dark:hover:bg-stone-800"
          >
            {loggingOut ? "Keluar..." : "Keluar"}
          </button>
        )}
      </header>

      <main className="flex flex-1 items-center justify-center px-4 pb-16">
        {state.kind === "loading" && <LoadingCard />}
        {state.kind === "error" && <ErrorCard onRetry={() => load()} />}
        {state.kind === "ready" && <SuccessCard user={state.user} />}
      </main>
    </div>
  );
}

function SuccessCard({ user }: { user: User }) {
  const firstName = (user.name ?? user.email).split(" ")[0];
  const needsClassroom = !user.classroom.granted || user.classroom.reauth_required;

  return (
    <section
      aria-labelledby="login-success"
      className="w-full max-w-md rounded-3xl border border-stone-200 bg-white p-8 text-center shadow-sm dark:border-stone-800 dark:bg-stone-900"
    >
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400">
        <svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
          <path d="M5 12.5l4.5 4.5L19 7.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>

      <h1 id="login-success" className="mt-5 text-2xl font-bold">
        Berhasil masuk
      </h1>
      <p className="mt-2 text-stone-600 dark:text-stone-400">
        Halo, {firstName}! Akun Google kamu sudah terhubung dengan EduPad.
      </p>

      <div className="mt-6 flex items-center gap-3 rounded-2xl bg-stone-100 p-3 text-left dark:bg-stone-800">
        <Avatar user={user} />
        <div className="min-w-0">
          <p className="truncate font-semibold">{user.name ?? user.email}</p>
          <p className="truncate text-sm text-stone-600 dark:text-stone-400">{user.email}</p>
        </div>
      </div>

      {needsClassroom && (
        <div className="mt-4 rounded-2xl border border-amber-300 bg-amber-50 p-4 text-left text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
          <p>
            {user.classroom.reauth_required
              ? "Izin Google Classroom perlu diperbarui."
              : "Izin Google Classroom belum diberikan, jadi tugas dan materi Classroom belum bisa dibaca EduPad."}
          </p>
          <a
            href={CONSENT_URL}
            className="mt-2 inline-block font-semibold underline underline-offset-2 hover:no-underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-600"
          >
            Beri izin Classroom
          </a>
        </div>
      )}
    </section>
  );
}

function Avatar({ user }: { user: User }) {
  const [failed, setFailed] = useState(false);
  const initial = (user.name ?? user.email).charAt(0).toUpperCase();
  if (user.picture && !failed) {
    return (
      <img
        src={user.picture}
        alt=""
        referrerPolicy="no-referrer"
        onError={() => setFailed(true)}
        className="h-11 w-11 shrink-0 rounded-full object-cover"
      />
    );
  }
  return (
    <span
      aria-hidden="true"
      className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-emerald-700 font-bold text-white"
    >
      {initial}
    </span>
  );
}

function LoadingCard() {
  return (
    <div
      role="status"
      aria-label="Memuat"
      className="w-full max-w-md animate-pulse rounded-3xl border border-stone-200 bg-white p-8 dark:border-stone-800 dark:bg-stone-900"
    >
      <div className="mx-auto h-14 w-14 rounded-full bg-stone-200 dark:bg-stone-800" />
      <div className="mx-auto mt-5 h-6 w-40 rounded bg-stone-200 dark:bg-stone-800" />
      <div className="mx-auto mt-3 h-4 w-64 rounded bg-stone-200 dark:bg-stone-800" />
      <div className="mt-6 h-16 rounded-2xl bg-stone-100 dark:bg-stone-800" />
    </div>
  );
}

function ErrorCard({ onRetry }: { onRetry: () => void }) {
  return (
    <div
      role="alert"
      className="w-full max-w-md rounded-3xl border border-stone-200 bg-white p-8 text-center dark:border-stone-800 dark:bg-stone-900"
    >
      <p className="font-semibold">Tidak bisa terhubung ke server EduPad.</p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-4 rounded-full bg-emerald-700 px-5 py-2 text-sm font-semibold text-white transition hover:bg-emerald-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 focus-visible:ring-offset-2"
      >
        Coba lagi
      </button>
    </div>
  );
}
