import type { ReactNode } from "react";

interface Props {
  title: string;
  /** Keterangan singkat, hanya bila judul belum cukup jelas. */
  note?: ReactNode;
  action?: ReactNode;
  strong?: boolean;
  className?: string;
  id?: string;
  children: ReactNode;
}

/** Kartu bagian halaman: judul (font piksel) + isi. */
export function Section({ title, note, action, strong, className, id, children }: Props) {
  return (
    <section id={id} className={`card section ${strong ? "strong" : ""} ${className ?? ""}`}>
      <div className="section-head">
        <div>
          <h2>{title}</h2>
          {note && <p>{note}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

/** Angka utama dengan label; `tone` mewarnai angkanya. */
export function Figure({ value, label, note, tone }: { value: ReactNode; label: string; note?: ReactNode; tone?: "good" | "warn" | "bad" }) {
  return (
    <div className="card figure">
      <b className={tone}>{value}</b>
      <span>{label}</span>
      {note && <small>{note}</small>}
    </div>
  );
}

/** Bar kemajuan 0-100. */
export function Bar({ value, tone, label }: { value: number; tone?: "good" | "warn" | "bad"; label?: string }) {
  const width = Math.max(0, Math.min(100, value));
  return (
    <div className={`bar ${tone ?? ""}`} role="meter" aria-label={label} aria-valuenow={Math.round(width)} aria-valuemin={0} aria-valuemax={100}>
      <i style={{ width: `${width}%` }} />
    </div>
  );
}
