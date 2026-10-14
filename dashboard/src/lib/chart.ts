/** Warna & gaya bersama Recharts. Grafik monokrom; biru hanya untuk aksen (latensi), merah untuk error. */
export const C = {
  ink: "#18181b",
  inkSoft: "#55555c",
  inkFaint: "#a1a1a6",
  accent: "#2f5bea",
  bad: "#d92d20",
  muted: "#8b8b92",
  grid: "#ececea",
};

export const MONO = '"Geist Mono", ui-monospace, "Cascadia Code", Consolas, monospace';

export const axisProps = {
  stroke: C.muted,
  tick: { fill: C.muted, fontSize: 11, fontFamily: MONO },
  tickLine: false,
  axisLine: false,
} as const;

export const cursorProps = { fill: "rgba(24, 24, 27, 0.04)" } as const;
