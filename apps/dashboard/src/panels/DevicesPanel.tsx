import { Dot, Panel } from "../components/Panel";
import type { Device } from "../api/types";
import { ago, secs } from "../lib/format";

function deviceTone(d: Device) {
  if (!d.online) return "off";
  if ((d.battery_pct != null && d.battery_pct < 20) || (d.rssi_dbm != null && d.rssi_dbm < -75)) return "warn";
  return "good";
}

const TONE_LABEL = { off: "Offline", warn: "Perlu dicek", good: "Online" } as const;

export function DevicesPanel() {
  return (
    <Panel panel="devices" title="Perangkat" subtitle="ESP32-S3 yang terhubung ke server">
      {({ devices }) => (
        <div className="table-wrap bleed">
          <table>
            <thead>
              <tr>
                <th>Perangkat</th>
                <th>Terakhir</th>
                <th className="num">Baterai</th>
                <th className="num">Wi-Fi</th>
                <th className="num">Latensi</th>
                <th className="center">
                  <span className="sr-only">Status</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {devices.map((d) => {
                const tone = deviceTone(d);
                return (
                  <tr key={d.id}>
                    <td>
                      <div className="cell-strong">{d.name}</div>
                      <div className="cell-sub mono">{d.id}</div>
                    </td>
                    <td className={d.online ? undefined : "muted"}>{ago(d.last_seen)}</td>
                    <td className={`num mono ${d.battery_pct != null && d.battery_pct < 20 ? "bad-text" : ""}`}>
                      {d.battery_pct == null ? "—" : `${d.battery_pct}%`}
                    </td>
                    <td className="num mono">{d.rssi_dbm == null ? "—" : d.rssi_dbm}</td>
                    <td className="num mono">{secs(d.avg_latency_s)}</td>
                    <td className="center" title={TONE_LABEL[tone]}>
                      <Dot tone={tone} />
                      <span className="sr-only">{TONE_LABEL[tone]}</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className="table-note">Wi-Fi dalam dBm · latensi rata-rata /v1/ask</p>
        </div>
      )}
    </Panel>
  );
}
