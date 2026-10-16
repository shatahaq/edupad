import { useEffect, useRef, useState, type FormEvent } from "react";
import { usePanel } from "../api/usePanel";
import { MONITOR_SECTIONS, NAV_ITEMS } from "../lib/nav";
import { go, type Page } from "../lib/router";
import { Icon } from "./Icon";

const IS_MAC = typeof navigator !== "undefined" && /Mac|iPhone|iPad/.test(navigator.platform);
const DAY_MS = 86_400_000;

/** Yang bisa dicari: halaman, lalu kartu di Monitoring. */
const TARGETS = [
  ...NAV_ITEMS.filter((i) => i.target !== false).map((i) => ({ label: i.label, page: i.id as Page, section: undefined as string | undefined })),
  ...MONITOR_SECTIONS.map((s) => ({ label: `Monitoring: ${s.label}`, page: "monitoring" as Page, section: s.id as string })),
];

export function Topbar({ page, onMenu }: { page: string; onMenu: () => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");

  // Lonceng menyala bila ada yang perlu segera ditindaklanjuti mahasiswa.
  const openPresence = usePanel("attendance").data?.today.some((m) => m.window === "dibuka") ?? false;
  const dueSoon =
    usePanel("assignments").data?.tasks.some((t) => !t.submitted && t.deadline && new Date(t.deadline).getTime() - Date.now() < DAY_MS) ?? false;
  const alerting = openPresence || dueSoon;

  // ⌘K / Ctrl+K memfokuskan pencarian.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        input.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // Enter = buka halaman / kartu pertama yang namanya cocok.
  const submit = (e: FormEvent) => {
    e.preventDefault();
    const q = query.trim().toLowerCase();
    const hit = q && TARGETS.find((t) => t.label.toLowerCase().includes(q));
    if (hit) {
      go(hit.page, hit.section);
      setQuery("");
      input.current?.blur();
    }
  };

  return (
    <header className="topbar">
      <button className="icon-btn hamburger" onClick={onMenu} aria-label="Buka menu">
        <Icon name="menu" />
      </button>

      <nav className="crumbs" aria-label="Breadcrumb">
        <span className="crumb-root">EduPad</span>
        <span className="crumb-sep" aria-hidden>
          ›
        </span>
        <span className="crumb-current" aria-current="page">
          {page}
        </span>
      </nav>

      <form className="search" role="search" onSubmit={submit}>
        <Icon name="search" size={14} />
        <input
          ref={input}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Cari halaman…"
          aria-label="Cari halaman"
          list="nav-search"
        />
        <kbd>{IS_MAC ? "⌘K" : "Ctrl K"}</kbd>
        <datalist id="nav-search">
          {TARGETS.map((t) => (
            <option key={t.label} value={t.label} />
          ))}
        </datalist>
      </form>

      <button
        className="icon-btn bell"
        onClick={() => go("beranda")}
        aria-label={alerting ? "Notifikasi: ada presensi dibuka atau deadline dekat" : "Notifikasi"}
        title={alerting ? "Ada presensi dibuka atau deadline < 24 jam" : "Notifikasi"}
      >
        <Icon name="bell" />
        {alerting && <i className="bell-dot" />}
      </button>
    </header>
  );
}
