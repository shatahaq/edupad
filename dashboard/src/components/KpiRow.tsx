import type { ReactNode } from "react";
import { usePanel } from "../api/usePanel";
import { dec, num, secs } from "../lib/format";

export interface KpiProps {
  label: string;
  value: ReactNode;
  unit?: string;
  /** Deret untuk mini bar chart, urut waktu naik; tanpa deret = tanpa grafik. */
  bars?: number[];
  barsLabel?: string;
  /** Bar yang ditebalkan; default: bar terakhir (jam berjalan). */
  strong?: (i: number) => boolean;
  foot: ReactNode;
}

/** Kartu angka utama: label, angka mono besar, mini bar chart opsional, footer keterangan. */
export function Kpi({ label, value, unit, bars, barsLabel, strong = (i) => i === (bars?.length ?? 0) - 1, foot }: KpiProps) {
  const max = Math.max(...(bars ?? []), 0) || 1;
  return (
    <article className="card kpi">
      <div className="kpi-body">
        <div>
          <div className="kpi-label">{label}</div>
          <div className="kpi-value">
            {value}
            {unit && <span className="unit">{unit}</span>}
          </div>
        </div>
        {bars && (
          <div className="spark" role="img" aria-label={barsLabel}>
            {bars.map((v, i) => (
              <span key={i} className={strong(i) ? "now" : undefined} style={{ height: `${Math.max(6, (v / max) * 100)}%` }} />
            ))}
          </div>
        )}
      </div>
      <div className="kpi-foot">{foot}</div>
    </article>
  );
}

export const DASH = "—";

/** Empat angka utama monitoring; memakai data panel api & devices (fetch dibagi dengan kartunya). */
export function MonitoringKpis() {
  const api = usePanel("api").data;
  const devices = usePanel("devices").data?.devices;

  const series = api?.series ?? [];
  const success = api && api.requests ? (api.by_status.ok / api.requests) * 100 : null;
  const online = devices?.filter((d) => d.online) ?? [];
  const offline = devices?.filter((d) => !d.online) ?? [];

  return (
    <section className="kpis" aria-label="Indikator utama">
      <Kpi
        label="Permintaan"
        value={api ? num(api.requests) : DASH}
        bars={series.map((p) => p.requests)}
        barsLabel="Permintaan per jam"
        foot={
          <>
            ok <b>{api ? num(api.by_status.ok) : DASH}</b>
            <span className="sep">·</span>
            {api?.window_hours ?? 24} jam
          </>
        }
      />
      <Kpi
        label="Berhasil"
        value={success == null ? DASH : dec(success)}
        unit="%"
        bars={series.map((p) => (p.requests ? (p.requests - p.errors) / p.requests : 1))}
        barsLabel="Tingkat berhasil per jam"
        foot={
          <>
            error server <b className={api?.by_status.server_error ? "bad-text" : undefined}>{api ? num(api.by_status.server_error) : DASH}</b>
          </>
        }
      />
      <Kpi
        label="Latensi rata-rata"
        value={api ? dec(api.latency_avg_s) : DASH}
        unit="dtk"
        bars={series.map((p) => p.latency_avg_s)}
        barsLabel="Latensi rata-rata per jam"
        foot={
          <>
            p95 <b>{api ? secs(api.latency_p95_s) : DASH}</b>
            <span className="sep">·</span>
            target {api ? secs(api.latency_goal_s) : DASH}
          </>
        }
      />
      <Kpi
        label="Perangkat online"
        value={devices ? online.length : DASH}
        unit={devices ? `dari ${devices.length}` : undefined}
        bars={(devices ?? []).map((d) => (d.online ? 1 : 0.15))}
        barsLabel="Status tiap perangkat"
        strong={(i) => !!devices?.[i].online}
        foot={
          !devices ? (
            DASH
          ) : offline.length ? (
            <>
              <span className="name">{offline.map((d) => d.name).join(", ")}</span> offline
            </>
          ) : (
            "semua online"
          )
        }
      />
    </section>
  );
}
