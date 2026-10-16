import { useEffect, useState } from "react";

import { GoogleIcon } from "../components/GoogleIcon";
import { Wordmark } from "../components/Wordmark";
import { LOGIN_URL, fetchMe, loginErrorMessage } from "../lib/api";

export default function Landing() {
  // Pesan dari `/?error=<kode>` (login gagal) dibaca sekali, lalu dihapus dari URL.
  const [error] = useState(() =>
    loginErrorMessage(new URLSearchParams(window.location.search).get("error")),
  );
  const [redirecting, setRedirecting] = useState(false);

  useEffect(() => {
    if (window.location.search) window.history.replaceState(null, "", "/");
    // Sudah login (cookie sesi masih berlaku): langsung ke dashboard.
    const controller = new AbortController();
    fetchMe(controller.signal)
      .then(() => window.location.replace("/dashboard/")) // dashboard EduPad (dashboard/)
      .catch(() => {}); // belum login / server mati: tetap di halaman ini
    return () => controller.abort();
  }, []);

  useEffect(() => {
    // Kembali dengan tombol Back dari halaman Google: browser memulihkan halaman dari
    // cache, jadi tombol jangan tertahan dalam keadaan memuat.
    const reset = (event: PageTransitionEvent) => {
      if (event.persisted) setRedirecting(false);
    };
    window.addEventListener("pageshow", reset);
    return () => window.removeEventListener("pageshow", reset);
  }, []);

  return (
    <main className="flex min-h-dvh flex-col items-center justify-center gap-10 px-4 py-16">
      <h1 className="text-6xl sm:text-7xl">
        <Wordmark />
      </h1>

      <div className="flex w-full max-w-xs flex-col items-center gap-4">
        <a
          href={LOGIN_URL}
          onClick={() => setRedirecting(true)}
          aria-busy={redirecting}
          className="inline-flex h-12 w-full items-center justify-center gap-3 rounded-full border border-stone-300 bg-white px-6 text-[15px] font-semibold text-stone-800 shadow-sm transition hover:bg-stone-100 hover:shadow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 focus-visible:ring-offset-2 focus-visible:ring-offset-stone-50 aria-busy:pointer-events-none aria-busy:opacity-70 dark:border-stone-700 dark:bg-stone-900 dark:text-stone-100 dark:hover:bg-stone-800 dark:focus-visible:ring-offset-stone-950"
        >
          {redirecting ? (
            <span
              className="h-5 w-5 animate-spin rounded-full border-2 border-stone-300 border-t-emerald-600"
              aria-hidden="true"
            />
          ) : (
            <GoogleIcon />
          )}
          Masuk dengan Google
        </a>

        {error && (
          <p role="alert" className="text-center text-sm text-red-700 dark:text-red-400">
            {error}
          </p>
        )}
      </div>
    </main>
  );
}
