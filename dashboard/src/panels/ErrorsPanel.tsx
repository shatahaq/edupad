import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ErrorsData } from "../api/types";
import { ChartTooltip } from "../components/ChartTooltip";
import { Panel, SectionLabel, Stat } from "../components/Panel";
import { axisProps, C, cursorProps } from "../lib/chart";
import { ago, hourLabel, num } from "../lib/format";

type Hour = ErrorsData["by_hour"][number];

export function ErrorsPanel() {
  return (
    <Panel panel="errors" title="Error" subtitle="Per jam, 24 jam terakhir">
      {(d) => {
        const total = d.by_hour.reduce((s, h) => s + h.count, 0);
        const peak = d.by_hour.reduce((a, b) => (b.count > a.count ? b : a), d.by_hour[0]);
        return (
          <>
            <div className="stats">
              <Stat label="Total error" value={num(total)} hint="24 jam" />
              {peak && peak.count > 0 && <Stat label="Jam terbanyak" value={hourLabel(peak.time)} hint={`${peak.count} error`} />}
            </div>

            <div className="chart" style={{ height: 112 }}>
              <ResponsiveContainer>
                <BarChart data={d.by_hour} margin={{ top: 4, right: 0, left: -30, bottom: 0 }} barCategoryGap="30%">
                  <CartesianGrid vertical={false} stroke={C.grid} />
                  <XAxis dataKey="time" tickFormatter={hourLabel} interval={5} {...axisProps} />
                  <YAxis allowDecimals={false} {...axisProps} />
                  <Tooltip
                    cursor={cursorProps}
                    content={<ChartTooltip<Hour> title={(p) => `${hourLabel(p.time)} WIB`} rows={(p) => [{ label: "Error", value: num(p.count), color: C.bad }]} />}
                  />
                  <Bar dataKey="count" fill={C.bad} isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="block">
              <SectionLabel>Paling sering</SectionLabel>
              <ul className="rows compact">
                {d.top.map((e) => (
                  <li key={e.kind}>
                    <span className="count-badge mono">{e.count}×</span>
                    <span className="row-main">{e.kind}</span>
                    <span className="cell-sub">{ago(e.last_at)}</span>
                  </li>
                ))}
              </ul>
            </div>
          </>
        );
      }}
    </Panel>
  );
}
