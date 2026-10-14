import type { ReactNode } from "react";
import { usePanel } from "../api/usePanel";
import type { DashboardData, PanelKey } from "../api/types";
import { hourLabel, num } from "../lib/format";
import { Icon } from "./Icon";

type Tone = "good" | "warn" | "bad";

interface Props<K extends PanelKey> {
  panel: K;
  title: string;
  subtitle?: string;
  className?: string;
  /** id elemen; default kunci panel. Isi bila satu halaman punya beberapa kartu dari panel yang sama. */
  id?: string;
  /** Aksi kecil di header, mis. tautan "Lihat semua". */
  action?: ReactNode;
  children: (data: DashboardData[K]) => ReactNode;
}

/** Kartu panel: ambil data sendiri, tampilkan loading / error / isi. `id` = kunci panel (target menu). */
export function Panel<K extends PanelKey>({ panel, id, title, subtitle, className, action, children }: Props<K>) {
  const { data, error, loading, updatedAt, reload } = usePanel(panel);

  return (
    <section id={id ?? panel} className={`card panel ${className ?? ""}`} aria-busy={loading}>
      <header className="panel-head">
        <div>
          <h2 className="card-title">{title}</h2>
          {subtitle && <p className="card-sub">{subtitle}</p>}
        </div>
        <div className="panel-actions">
          {action}
          <button className="icon-btn" onClick={reload} title="Muat ulang" aria-label={`Muat ulang ${title}`}>
            <Icon name="refresh" size={13} className={loading ? "spin" : undefined} />
          </button>
        </div>
      </header>

      <div className="panel-body">
        {error && (
          <div className="panel-error" role="alert">
            Gagal memuat: {error}
            {data && <span> · menampilkan data {updatedAt ? hourLabel(updatedAt.toISOString()) : "terakhir"}</span>}
          </div>
        )}
        {data ? children(data) : !error && <div className="skeleton" />}
      </div>
    </section>
  );
}

export function Stat({ label, value, unit, hint, tone }: { label: string; value: ReactNode; unit?: string; hint?: ReactNode; tone?: Tone }) {
  return (
    <div className="stat">
      <div className="stat-label">{label}</div>
      <div className="stat-value">
        {value}
        {unit && <span className="unit">{unit}</span>}
      </div>
      {hint && (
        <div className={`stat-hint ${tone ?? ""}`}>
          {tone && <Dot tone={tone} />}
          {hint}
        </div>
      )}
    </div>
  );
}

/** Meter horizontal. Hitam (atau biru bila `accent`), berubah oranye ≥75% dan merah ≥90%. */
export function Meter({ value, max = 100, accent, label }: { value: number; max?: number; accent?: boolean; label?: string }) {
  const w = Math.min(100, (value / max) * 100);
  const t = w >= 90 ? "bad" : w >= 75 ? "warn" : accent ? "accent" : "ink";
  return (
    <div className="meter" role="meter" aria-label={label} aria-valuenow={value} aria-valuemin={0} aria-valuemax={max}>
      <div className={`meter-fill ${t}`} style={{ width: `${w}%` }} />
    </div>
  );
}

export function Dot({ tone }: { tone: Tone | "off" }) {
  return <span className={`dot ${tone}`} aria-hidden />;
}

export function SectionLabel({ children }: { children: ReactNode }) {
  return <h3 className="section-label">{children}</h3>;
}

/** Daftar bar horizontal sederhana: label, trek, nilai mono. */
export function BarList({ items, unit }: { items: { label: string; value: number; title?: string }[]; unit?: string }) {
  const max = Math.max(1, ...items.map((i) => i.value));
  return (
    <ol className="bars">
      {items.map((i) => (
        <li key={i.label} title={i.title}>
          <span className="bars-label">{i.label}</span>
          <span className="bars-track">
            <span style={{ width: `${(i.value / max) * 100}%` }} />
          </span>
          <span className="mono num">
            {num(i.value)}
            {unit}
          </span>
        </li>
      ))}
    </ol>
  );
}
