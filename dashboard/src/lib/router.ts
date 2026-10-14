import { useSyncExternalStore } from "react";

/** Halaman dashboard; dipetakan ke hash `#/<page>[/<bagian>]` agar link bisa dibagikan dan tombol back jalan. */
export const PAGES = ["beranda", "presensi", "tugas", "jadwal", "percakapan", "belajar", "monitoring"] as const;
export type Page = (typeof PAGES)[number];

export interface Route {
  page: Page;
  /** Bagian di dalam halaman (mis. kartu monitoring), opsional. */
  section: string | null;
}

let current = parse();

function parse(): Route {
  const [page, section] = window.location.hash.replace(/^#\/?/, "").split("/");
  return (PAGES as readonly string[]).includes(page) ? { page: page as Page, section: section || null } : { page: "beranda", section: null };
}

function subscribe(listener: () => void) {
  const onChange = () => {
    current = parse();
    listener();
  };
  window.addEventListener("hashchange", onChange);
  return () => window.removeEventListener("hashchange", onChange);
}

export function useRoute(): Route {
  return useSyncExternalStore(subscribe, () => current);
}

export function go(page: Page, section?: string) {
  const hash = page === "beranda" && !section ? "#/" : `#/${page}${section ? `/${section}` : ""}`;
  if (window.location.hash === hash) {
    // Hash sama (mis. klik bagian yang sama lagi): tetap beri tahu pendengar.
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  } else {
    window.location.hash = hash;
  }
}
