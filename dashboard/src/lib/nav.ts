import type { IconName } from "../components/Icon";
import type { OwlName } from "./owls";
import type { Page } from "./router";

export type NavId = Page;

export interface NavItem {
  id: NavId;
  label: string;
  icon: IconName;
  /** Owl pemandu halaman (warna ikon di menu). Tanpa owl = halaman sistem. */
  owl?: OwlName;
}

export const NAV: { group: string; items: NavItem[] }[] = [
  {
    group: "Hari ini",
    items: [
      { id: "beranda", label: "Beranda", icon: "home", owl: "nova" },
      { id: "office", label: "AI Office", icon: "bot", owl: "nova" },
    ],
  },
  {
    group: "Kuliah",
    items: [
      { id: "tugas", label: "Tugas", icon: "clipboard", owl: "tempo" },
      { id: "presensi", label: "Presensi", icon: "calendarCheck", owl: "tempo" },
      { id: "jadwal", label: "Jadwal", icon: "calendar", owl: "tempo" },
    ],
  },
  {
    group: "Belajar",
    items: [
      { id: "tutor", label: "Tutor Belajar", icon: "sparkle", owl: "sora" },
      { id: "equity", label: "Equity Radar", icon: "activity", owl: "nexus" },
      { id: "belajar", label: "Riwayat belajar", icon: "book", owl: "metric" },
      { id: "percakapan", label: "Percakapan", icon: "message", owl: "pixel" },
    ],
  },
  {
    group: "Pribadi",
    items: [{ id: "keuangan", label: "Keuangan", icon: "wallet", owl: "koin" }],
  },
  {
    group: "Lainnya",
    items: [
      { id: "monitoring", label: "Monitoring", icon: "gauge" },
      { id: "pengaturan", label: "Pengaturan", icon: "sliders" },
      { id: "bantuan", label: "Cara pakai", icon: "help" },
    ],
  },
];

export const NAV_ITEMS = NAV.flatMap((g) => g.items);

export const pageLabel = (page: Page) => NAV_ITEMS.find((i) => i.id === page)?.label ?? "AI Office";
