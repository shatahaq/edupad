import type { PanelKey } from "../api/types";
import type { IconName } from "../components/Icon";
import type { Page } from "./router";

export type NavId = Page;

export interface NavItem {
  id: NavId;
  label: string;
  icon: IconName;
  /** false = belum ada halaman tujuan. */
  target?: false;
}

export const NAV: { group: string; items: NavItem[] }[] = [
  {
    group: "Kantor AI",
    items: [{ id: "office", label: "AI Office", icon: "bot" }],
  },
  {
    group: "Belajar",
    items: [
      { id: "beranda", label: "Beranda", icon: "home" },
      { id: "presensi", label: "Presensi", icon: "calendarCheck" },
      { id: "tugas", label: "Tugas", icon: "clipboard" },
      { id: "jadwal", label: "Jadwal", icon: "calendar" },
      { id: "keuangan", label: "Keuangan", icon: "wallet" },
      { id: "percakapan", label: "Riwayat percakapan", icon: "message" },
      { id: "belajar", label: "Riwayat belajar", icon: "book" },
      { id: "equity", label: "Equity Radar", icon: "activity" },
    ],
  },
  {
    group: "Sistem",
    items: [{ id: "monitoring", label: "Monitoring", icon: "gauge" }],
  },
  {
    group: "Pengaturan",
    items: [
      { id: "pengaturan", label: "Pengaturan", icon: "sliders" },
      { id: "bantuan", label: "Bantuan", icon: "help" },
    ],
  },
];

export const NAV_ITEMS = NAV.flatMap((g) => g.items);

export const pageLabel = (page: Page) => NAV_ITEMS.find((i) => i.id === page)?.label ?? "AI Office";

/** Kartu di halaman Monitoring; id = kunci panel = id elemen kartu. */
export const MONITOR_SECTIONS: { id: PanelKey; label: string }[] = [
  { id: "api", label: "Kesehatan API" },
  { id: "devices", label: "Perangkat" },
  { id: "agent", label: "AI Agent" },
  { id: "cost", label: "Biaya API" },
  { id: "services", label: "Layanan luar" },
  { id: "knowledge", label: "Basis pengetahuan" },
  { id: "errors", label: "Error" },
  { id: "resources", label: "Server" },
  { id: "activity", label: "Aktivitas pengguna" },
];
