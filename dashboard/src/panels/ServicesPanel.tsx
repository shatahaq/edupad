import { Dot, Meter, Panel } from "../components/Panel";
import type { ServiceState } from "../api/types";
import { num, secs } from "../lib/format";

const TONE: Record<ServiceState, "good" | "warn" | "bad" | "off"> = { ok: "good", slow: "warn", down: "bad", unknown: "off" };
const LABEL: Record<ServiceState, string> = { ok: "Normal", slow: "Lambat", down: "Belum siap", unknown: "Belum diperiksa" };

export function ServicesPanel() {
  return (
    <Panel panel="services" title="Layanan luar" subtitle="Ketergantungan server">
      {({ services }) => (
        <ul className="rows">
          {services.map((s) => (
            <li key={s.id}>
              <Dot tone={TONE[s.state]} />
              <div className="row-main">
                <div className="cell-strong">{s.name}</div>
                <div className="cell-sub">{s.role}</div>
              </div>
              <div className="row-side">
                <span className={`pill ${TONE[s.state]}`}>{LABEL[s.state]}</span>
                <div className="cell-sub mono">
                  {s.avg_latency_s != null ? secs(s.avg_latency_s) : "—"}
                  {s.errors_24h > 0 && <span className="bad-text"> · {s.errors_24h} err</span>}
                </div>
              </div>
              {s.quota && (
                <div className="row-full">
                  <div className="meter-head small">
                    <span>Kuota bulanan</span>
                    <span className="mono">
                      {num(s.quota.used)} / {num(s.quota.limit)} {s.quota.unit}
                    </span>
                  </div>
                  <Meter value={s.quota.used} max={s.quota.limit} accent label={`Kuota ${s.name}`} />
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
