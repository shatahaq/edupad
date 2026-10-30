const nf = new Intl.NumberFormat("id-ID");
const timeFmt = new Intl.DateTimeFormat("id-ID", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Jakarta" });
const dateFmt = new Intl.DateTimeFormat("id-ID", { day: "numeric", month: "short", timeZone: "Asia/Jakarta" });

export const num = (n: number) => nf.format(n);
/** Desimal gaya Indonesia tanpa satuan: 3,0 */
export const dec = (n: number, digits = 1) => n.toFixed(digits).replace(".", ",");
export const pct = (n: number, digits = 0) => `${n.toFixed(digits).replace(".", ",")}%`;
export const secs = (n: number | null) => (n == null ? "—" : `${n.toFixed(1).replace(".", ",")} dtk`);
export const usd = (n: number, digits = 2) => `$${n.toFixed(digits)}`;
export const hourLabel = (iso: string) => timeFmt.format(new Date(iso));
export const dayLabel = (iso: string) => dateFmt.format(new Date(iso));

export function ago(iso: string | null): string {
  if (!iso) return "—";
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "baru saja";
  if (s < 3600) return `${Math.floor(s / 60)} mnt lalu`;
  if (s < 86400) return `${Math.floor(s / 3600)} jam lalu`;
  return `${Math.floor(s / 86400)} hari lalu`;
}

export function duration(s: number): string {
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  return d ? `${d} hari ${h} jam` : `${h} jam ${Math.floor((s % 3600) / 60)} mnt`;
}

const isoDateFmt = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Jakarta" });
const shortDayFmt = new Intl.DateTimeFormat("id-ID", { weekday: "short", day: "numeric", month: "short", timeZone: "Asia/Jakarta" });

/** Tanggal WIB "YYYY-MM-DD", untuk membandingkan hari. */
export const wibDate = (d: string | Date | number) => isoDateFmt.format(new Date(d));

/** "Hari ini" / "Besok" / "Kemarin" / "Sen, 14 Okt". */
export function dayHeading(iso: string): string {
  const day = wibDate(iso);
  const DAY = 86_400_000;
  if (day === wibDate(Date.now())) return "Hari ini";
  if (day === wibDate(Date.now() + DAY)) return "Besok";
  if (day === wibDate(Date.now() - DAY)) return "Kemarin";
  return shortDayFmt.format(new Date(iso));
}

/** Sisa waktu ke `iso`: "40 mnt lagi", "5 jam lagi", "2 hari lagi", atau "lewat 3 jam". */
export function countdown(iso: string): string {
  const diff = new Date(iso).getTime() - Date.now();
  const s = Math.abs(diff) / 1000;
  const span = s < 3600 ? `${Math.max(1, Math.round(s / 60))} mnt` : s < 86400 ? `${Math.floor(s / 3600)} jam` : `${Math.floor(s / 86400)} hari`;
  return diff >= 0 ? `${span} lagi` : `lewat ${span}`;
}
