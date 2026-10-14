import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { CostData } from "../api/types";
import { ChartTooltip } from "../components/ChartTooltip";
import { Meter, Panel, Stat } from "../components/Panel";
import { axisProps, C } from "../lib/chart";
import { dayLabel, usd } from "../lib/format";

type Day = CostData["daily"][number];

export function CostPanel() {
  return (
    <Panel panel="cost" title="Biaya API" subtitle="Bulan berjalan">
      {(d) => {
        const forecastPct = (d.forecast_usd / d.budget_month_usd) * 100;
        const usedPct = (d.total_usd / d.budget_month_usd) * 100;
        return (
          <>
            <div className="stats">
              <Stat label="Terpakai" value={usd(d.total_usd)} hint={d.month} />
              <Stat
                label="Perkiraan akhir bulan"
                value={usd(d.forecast_usd)}
                hint={forecastPct > 100 ? "melebihi anggaran" : forecastPct > 80 ? "mendekati anggaran" : "dalam anggaran"}
                tone={forecastPct > 100 ? "bad" : forecastPct > 80 ? "warn" : "good"}
              />
            </div>

            <div className="block">
              <div className="meter-head">
                <span>Anggaran</span>
                <span className="mono">
                  {usd(d.total_usd)} / {usd(d.budget_month_usd)} · {Math.round(usedPct)}%
                </span>
              </div>
              <Meter value={d.total_usd} max={d.budget_month_usd} label="Anggaran terpakai" />
            </div>

            <div className="chart" style={{ height: 112 }}>
              <ResponsiveContainer>
                <AreaChart data={d.daily} margin={{ top: 6, right: 0, left: -22, bottom: 0 }}>
                  <CartesianGrid vertical={false} stroke={C.grid} />
                  <XAxis dataKey="date" tickFormatter={dayLabel} interval="preserveStartEnd" minTickGap={28} {...axisProps} />
                  <YAxis tickFormatter={(v: number) => `$${v}`} {...axisProps} />
                  <Tooltip
                    cursor={{ stroke: C.muted, strokeDasharray: "3 3" }}
                    content={<ChartTooltip<Day> title={(p) => dayLabel(p.date)} rows={(p) => [{ label: "Biaya", value: usd(p.usd, 3), color: C.ink }]} />}
                  />
                  <Area dataKey="usd" stroke={C.ink} fill={C.ink} fillOpacity={0.06} strokeWidth={1.5} isAnimationActive={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <ul className="kv">
              {d.by_service.map((s) => (
                <li key={s.service}>
                  <span>{s.service}</span>
                  <span className="mono">{s.usd === 0 ? <span className="muted">gratis</span> : usd(s.usd)}</span>
                </li>
              ))}
            </ul>
          </>
        );
      }}
    </Panel>
  );
}
