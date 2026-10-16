/** Warna & gaya bersama Recharts. Grafik monokrom; biru hanya untuk aksen (latensi), merah untuk error. */
export const C = {
  ink: "#3d4a58",
  inkSoft: "#5f6b78",
  inkFaint: "#b9b0a2",
  accent: "#1d727a",
  bad: "#c2414b",
  muted: "#5f6b78",
  grid: "#ebe2d3",
};

export const MONO = '"Geist Mono", ui-monospace, "Cascadia Code", Consolas, monospace';

export const axisProps = {
  stroke: C.muted,
  tick: { fill: C.muted, fontSize: 11, fontFamily: MONO },
  tickLine: false,
  axisLine: false,
} as const;

export const cursorProps = { fill: "rgba(24, 24, 27, 0.04)" } as const;
