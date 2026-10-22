import type { ReactNode } from "react";

import type { Lang } from "../../../web/src/landing/copy";

// Bagian-bagian kecil yang dipakai berulang di halaman depan versi neo-brutalism.
// Aturan bentuknya ada di DESIGN.md: tepi hitam 3 px, bayangan blok, sudut siku.

export const SHELL = "mx-auto w-full max-w-6xl px-4 sm:px-6";

/** Label kecil di atas judul bagian. */
export function Eyebrow({ children, tone = "dark" }: { children: ReactNode; tone?: "dark" | "light" }) {
  const style = tone === "dark" ? "bg-ink text-paper" : "bg-paper text-ink";
  return <span className={`inline-block border-3 border-ink px-3 py-1 font-display text-xs uppercase tracking-[0.12em] ${style}`}>{children}</span>;
}

export function SectionTitle({ id, children, className = "" }: { id: string; children: ReactNode; className?: string }) {
  return (
    <h2 id={id} className={`font-display text-[clamp(2rem,4.4vw,3rem)] leading-[1.03] ${className}`}>
      {children}
    </h2>
  );
}

/** Pemilih bahasa: satu-satunya bentuk membulat di halaman ini. */
export function LangSwitch({ lang, setLang, label, tone = "dark" }: { lang: Lang; setLang: (l: Lang) => void; label: string; tone?: "dark" | "light" }) {
  const on = tone === "dark" ? "bg-ink text-paper" : "bg-paper text-ink";
  const off = tone === "dark" ? "text-ink hover:bg-bone" : "text-paper hover:bg-ink-2";
  return (
    <div role="group" aria-label={label} className={`flex border-3 border-ink p-0.5 ${tone === "dark" ? "bg-paper" : "bg-ink"}`}>
      {(["id", "en"] as const).map((code) => (
        <button
          key={code}
          type="button"
          lang={code}
          aria-pressed={lang === code}
          onClick={() => setLang(code)}
          className={`h-8 w-10 font-display text-xs uppercase transition-colors ${lang === code ? on : off}`}
        >
          {code}
        </button>
      ))}
    </div>
  );
}

/** Baris berjalan berisi empat langkah kerja EduPad; berhenti bila pengguna meminta sedikit gerak. */
export function Marquee({ items }: { items: string[] }) {
  const run = [...items, ...items];
  return (
    <div className="overflow-hidden border-y-3 border-ink bg-ink py-3" aria-hidden="true">
      <div className="flex w-max animate-marquee">
        {run.map((item, index) => (
          <span key={index} className="flex items-center gap-6 whitespace-nowrap px-6 font-display text-sm uppercase tracking-wide text-paper">
            {item}
            <span className="inline-block h-2 w-2 bg-pop-yellow" />
          </span>
        ))}
      </div>
    </div>
  );
}

export function Source({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="mt-auto pt-4 text-sm font-semibold text-ink-2 underline decoration-ink/30 underline-offset-4 hover:decoration-ink"
    >
      {children}
    </a>
  );
}

type ChartData = { value: string; label: string; note: string; source: string; url: string };

/** Statistik besar + grafiknya. Angka memakai huruf teks (tabular), bukan huruf judul. */
export function StatCard({ data, accent, children }: { data: ChartData; accent: string; children: ReactNode }) {
  return (
    <figure className="flex flex-col border-3 border-ink bg-paper shadow-neo">
      <div className="border-b-3 border-ink p-5 sm:p-6" style={{ backgroundColor: accent }}>
        <p className="nums text-[clamp(2.5rem,5vw,3.5rem)] font-bold leading-none tracking-tight">{data.value}</p>
        <p className="mt-2 text-lg font-semibold">{data.label}</p>
      </div>
      <div className="flex flex-1 flex-col p-5 sm:p-6">
        <div className="max-w-md">{children}</div>
        <figcaption className="mt-4 text-[16px] text-ink-2">{data.note}</figcaption>
        <Source href={data.url}>{data.source}</Source>
      </div>
    </figure>
  );
}

const INK = "#111111";
const CYAN = "#35C8F3";
const YELLOW = "#FFD400";

/** Dua batang: dua dekade lalu (kurang dari separuh) vs 2024. Sumber hanya menyebut "lebih dari
 *  dua kali lipat", jadi batang kiri sengaja tanpa angka. */
export function EnrolmentBars({ before, after, growth, label }: { before: string; after: string; growth: string; label: string }) {
  return (
    <svg viewBox="0 0 320 180" role="img" aria-label={label} className="h-auto w-full" shapeRendering="crispEdges">
      <rect x="64" y="84" width="68" height="60" fill="#F3EADA" stroke={INK} strokeWidth="3" />
      <rect x="188" y="24" width="68" height="120" fill={CYAN} stroke={INK} strokeWidth="3" />
      <line x1="12" y1="145.5" x2="308" y2="145.5" stroke={INK} strokeWidth="3" />
      <rect x="236" y="2" width="72" height="28" fill={YELLOW} stroke={INK} strokeWidth="3" />
      <text x="272" y="22" textAnchor="middle" fontSize="16" fontWeight="700" fill={INK} fontFamily="inherit">
        {growth}
      </text>
      <text x="98" y="168" textAnchor="middle" fontSize="13" fontWeight="600" fill="#3A3A3A" fontFamily="inherit">
        {before}
      </text>
      <text x="222" y="168" textAnchor="middle" fontSize="13" fontWeight="700" fill={INK} fontFamily="inherit">
        {after}
      </text>
    </svg>
  );
}

/** Rasio kelulusan 22% (2013) -> 27% (2024) pada skala 0–40%. Garis putus-putus menandai bahwa
 *  tidak ada data tahunan di antara kedua titik itu. */
export function GraduationLine({ from, to, label }: { from: string; to: string; label: string }) {
  const y = (percent: number) => 144 - (percent / 40) * 120;
  return (
    <svg viewBox="0 0 320 180" role="img" aria-label={label} className="h-auto w-full" shapeRendering="crispEdges">
      <line x1="46" y1="20" x2="46" y2="145.5" stroke={INK} strokeWidth="3" />
      <line x1="46" y1="145.5" x2="308" y2="145.5" stroke={INK} strokeWidth="3" />
      <text x="38" y="26" textAnchor="end" fontSize="12" fill="#3A3A3A" fontFamily="inherit">
        40%
      </text>
      <text x="38" y="149" textAnchor="end" fontSize="12" fill="#3A3A3A" fontFamily="inherit">
        0%
      </text>
      <line x1="70" y1={y(22)} x2="276" y2={y(27)} stroke={INK} strokeWidth="4" strokeDasharray="12 8" />
      <rect x="60" y={y(22) - 10} width="20" height="20" fill="#F3EADA" stroke={INK} strokeWidth="3" />
      <rect x="266" y={y(27) - 10} width="20" height="20" fill={CYAN} stroke={INK} strokeWidth="3" />
      <text x="70" y={y(22) - 20} textAnchor="middle" fontSize="18" fontWeight="700" fill={INK} fontFamily="inherit">
        22%
      </text>
      <text x="276" y={y(27) - 20} textAnchor="middle" fontSize="18" fontWeight="700" fill={INK} fontFamily="inherit">
        27%
      </text>
      <text x="70" y="168" textAnchor="middle" fontSize="13" fontWeight="600" fill="#3A3A3A" fontFamily="inherit">
        {from}
      </text>
      <text x="276" y="168" textAnchor="middle" fontSize="13" fontWeight="700" fill={INK} fontFamily="inherit">
        {to}
      </text>
    </svg>
  );
}
