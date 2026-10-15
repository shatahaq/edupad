import { Meter, Panel, Stat } from "../components/Panel";
import { duration, num, pct } from "../lib/format";

export function ResourcesPanel() {
  return (
    <Panel panel="resources" title="Server" subtitle="Sumber daya VPS">
      {(d) => {
        const rows = [
          { label: "CPU", value: d.cpu_pct, hint: d.cpu_pct == null ? "—" : pct(d.cpu_pct) },
          { label: "Memori", value: d.memory_pct, hint: d.memory_pct == null || d.memory_used_mb == null || d.memory_total_mb == null ? "—" : `${num(d.memory_used_mb)} / ${num(d.memory_total_mb)} MB · ${pct(d.memory_pct)}` },
          { label: "Disk", value: d.disk_pct, hint: d.disk_pct == null ? "—" : pct(d.disk_pct) },
        ];
        return (
          <>
            <div className="meters">
              {rows.map((r) => (
                <div key={r.label}>
                  <div className="meter-head">
                    <span>{r.label}</span>
                    <span className="mono">{r.hint}</span>
                  </div>
                  <Meter value={r.value ?? 0} label={r.label} />
                </div>
              ))}
            </div>
            <div className="stats divided">
              <Stat label="Sesi aktif" value={d.active_sessions} hint="perangkat terhubung" />
              <Stat label="Uptime" value={<span className="stat-text">{duration(d.uptime_s)}</span>} hint="sejak restart terakhir" />
            </div>
          </>
        );
      }}
    </Panel>
  );
}
