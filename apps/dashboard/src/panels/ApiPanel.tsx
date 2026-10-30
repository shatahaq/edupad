import { Bar, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ApiHealthData } from "../api/types";
import { ChartTooltip } from "../components/ChartTooltip";
import { Panel } from "../components/Panel";
import { axisProps, C, cursorProps } from "../lib/chart";
import { dec, hourLabel, num, secs } from "../lib/format";

type Point = ApiHealthData["series"][number] & { ok: number };

export function ApiPanel() {
  return (
    <Panel panel="api" title="Kesehatan API" subtitle="POST /v1/ask, 24 jam terakhir">
      {(d) => {
        // Error ditumpuk di atas permintaan berhasil, jadi tinggi bar = total permintaan.
        const data: Point[] = d.series.map((p) => ({ ...p, ok: Math.max(0, p.requests - p.errors) }));
        return (
          <>
            {/* Mengikuti tinggi layar (mis. 730px pada zoom 125%), maks. 232px seperti di 1920×1080. */}
            <div className="chart" style={{ height: "clamp(180px, 28vh, 232px)" }}>
              <ResponsiveContainer>
                <ComposedChart data={data} margin={{ top: 8, right: 0, left: -18, bottom: 0 }} barCategoryGap="28%">
                  <CartesianGrid vertical={false} stroke={C.grid} />
                  <XAxis dataKey="time" tickFormatter={hourLabel} interval={3} {...axisProps} />
                  <YAxis yAxisId="req" allowDecimals={false} {...axisProps} />
                  <YAxis yAxisId="lat" orientation="right" tickFormatter={(v: number) => `${v}s`} width={34} {...axisProps} />
                  <Tooltip
                    cursor={cursorProps}
                    content={
                      <ChartTooltip<Point>
                        title={(p) => `${hourLabel(p.time)} WIB`}
                        rows={(p) => [
                          { label: "Permintaan", value: num(p.requests), color: C.ink },
                          { label: "Error", value: num(p.errors), color: C.bad },
                          { label: "Latensi", value: secs(p.latency_avg_s), color: C.accent },
                        ]}
                      />
                    }
                  />
                  <ReferenceLine yAxisId="lat" y={d.latency_goal_s} stroke={C.muted} strokeDasharray="4 4" />
                  <Bar yAxisId="req" dataKey="ok" stackId="r" fill={C.ink} isAnimationActive={false} />
                  <Bar yAxisId="req" dataKey="errors" stackId="r" fill={C.bad} isAnimationActive={false} />
                  <Line
                    yAxisId="lat"
                    dataKey="latency_avg_s"
                    stroke={C.accent}
                    strokeWidth={1.75}
                    dot={false}
                    activeDot={{ r: 3, strokeWidth: 0, fill: C.accent }}
                    isAnimationActive={false}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>

            <div className="chart-foot">
              <ul className="legend">
                <li>
                  <i style={{ background: C.ink }} />
                  Permintaan
                </li>
                <li>
                  <i style={{ background: C.bad }} />
                  Error
                </li>
                <li>
                  <i className="line" style={{ background: C.accent }} />
                  Latensi
                </li>
                <li>
                  <i className="dashed" />
                  Target {dec(d.latency_goal_s)} dtk
                </li>
              </ul>

              <div className="pills">
                <span className="pill good">
                  ok <b>{num(d.by_status.ok)}</b>
                </span>
                <span className="pill">
                  tanpa suara <b>{num(d.by_status.no_speech)}</b>
                </span>
                <span className="pill warn">
                  error klien <b>{num(d.by_status.client_error)}</b>
                </span>
                <span className="pill bad">
                  error server <b>{num(d.by_status.server_error)}</b>
                </span>
              </div>
            </div>
          </>
        );
      }}
    </Panel>
  );
}
