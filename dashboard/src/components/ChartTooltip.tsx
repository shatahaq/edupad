export interface TooltipRow {
  label: string;
  value: string;
  color?: string;
}

interface Props<T> {
  /** Diisi Recharts saat hover. */
  active?: boolean;
  payload?: { payload: T }[];
  title: (d: T) => string;
  rows: (d: T) => TooltipRow[];
}

/** Tooltip grafik: judul + baris label/nilai mono. Dipakai lewat `<Tooltip content={...} />`. */
export function ChartTooltip<T>({ active, payload, title, rows }: Props<T>) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="tt">
      <div className="tt-title">{title(d)}</div>
      {rows(d).map((r) => (
        <div key={r.label} className="tt-row">
          <span>
            {r.color && <i style={{ background: r.color }} />}
            {r.label}
          </span>
          <span className="mono">{r.value}</span>
        </div>
      ))}
    </div>
  );
}
