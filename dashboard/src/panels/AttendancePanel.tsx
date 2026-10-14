import type { AttendanceMeeting, PresenceWindow } from "../api/types";
import { Panel, SectionLabel } from "../components/Panel";
import { countdown, dayHeading, hourLabel, pct } from "../lib/format";
import { go } from "../lib/router";

type Tone = "good" | "warn" | "bad";

const WINDOW: Record<PresenceWindow, { label: string; tone?: Tone }> = {
  dibuka: { label: "Dibuka", tone: "good" },
  belum_dibuka: { label: "Belum dibuka" },
  sudah_diisi: { label: "Hadir", tone: "good" },
  tutup: { label: "Terlewat", tone: "bad" },
  belum_dijadwalkan: { label: "Belum dijadwalkan" },
};

/** Keterangan jam yang paling berguna untuk status saat ini. */
function windowNote(m: AttendanceMeeting): string {
  if (!m.mulai || !m.selesai) return "jam belum ada";
  switch (m.window) {
    case "dibuka":
      return `tutup ${hourLabel(m.selesai)} · ${countdown(m.selesai)}`;
    case "belum_dibuka":
      return dayHeading(m.mulai) === "Hari ini" ? `buka ${hourLabel(m.mulai)} · ${countdown(m.mulai)}` : `buka ${hourLabel(m.mulai)}`;
    case "tutup":
      return `tutup ${hourLabel(m.selesai)}`;
    default:
      return `${hourLabel(m.mulai)}–${hourLabel(m.selesai)}`;
  }
}

export function AttendanceRow({ m }: { m: AttendanceMeeting }) {
  const w = WINDOW[m.window];
  return (
    <li className={`att ${m.window}`}>
      <div className="slot-time mono">
        {m.mulai ? hourLabel(m.mulai) : "—"}
        <span>{m.selesai ? hourLabel(m.selesai) : ""}</span>
      </div>
      <div className="row-main">
        <div className="cell-strong wrap">
          {m.course} <span className="muted mono">p{m.pertemuan}</span>
        </div>
        <div className="cell-sub wrap">
          {[m.topik, m.cara.length ? m.cara.join(" / ") : null].filter(Boolean).join(" · ") || "—"}
        </div>
      </div>
      <div className="row-side">
        <span className={`pill ${w.tone ?? ""}`}>{w.label}</span>
        <div className="cell-sub mono">{windowNote(m)}</div>
      </div>
    </li>
  );
}

/** Presensi hari ini (Beranda) atau hari ini + 7 hari ke depan, dikelompokkan per hari (halaman Presensi). */
export function AttendancePanel({ scope }: { scope: "today" | "week" }) {
  return (
    <Panel
      panel="attendance"
      title={scope === "today" ? "Presensi hari ini" : "Presensi"}
      subtitle={scope === "today" ? "Jendela presensi portal SATU" : "Hari ini dan 7 hari ke depan"}
      action={
        scope === "today" && (
          <button className="link-btn" onClick={() => go("presensi")}>
            Semua
          </button>
        )
      }
    >
      {(d) => {
        const groups = new Map<string, AttendanceMeeting[]>();
        if (scope === "week") {
          for (const m of d.upcoming) {
            const key = m.mulai ? dayHeading(m.mulai) : "Belum dijadwalkan";
            groups.set(key, [...(groups.get(key) ?? []), m]);
          }
        }
        return (
          <>
            {d.stale && <div className="note warn">Data presensi lebih dari 3 jam lalu; status di portal mungkin sudah berubah.</div>}

            <div className="block">
              {scope === "week" && <SectionLabel>Hari ini</SectionLabel>}
              {d.today.length ? (
                <ul className="rows">
                  {d.today.map((m) => (
                    <AttendanceRow key={m.id} m={m} />
                  ))}
                </ul>
              ) : (
                <p className="empty">Tidak ada presensi hari ini.</p>
              )}
            </div>

            {[...groups].map(([day, items]) => (
              <div className="block" key={day}>
                <SectionLabel>{day}</SectionLabel>
                <ul className="rows">
                  {items.map((m) => (
                    <AttendanceRow key={m.id} m={m} />
                  ))}
                </ul>
              </div>
            ))}
          </>
        );
      }}
    </Panel>
  );
}

/** Batas kehadiran yang umum dipakai untuk syarat ujian. */
const MIN_ATTENDANCE = 75;

export function AttendanceRecapPanel() {
  return (
    <Panel panel="attendance" id="attendance-recap" title="Rekap kehadiran" subtitle={`Per mata kuliah · batas ${MIN_ATTENDANCE}%`}>
      {(d) => {
        const hadir = d.recap.reduce((s, r) => s + r.hadir, 0);
        const total = d.recap.reduce((s, r) => s + r.pertemuan, 0);
        return (
          <>
            <div className="stats">
              <div className="stat">
                <div className="stat-label">Kehadiran total</div>
                <div className="stat-value">
                  {total ? Math.round((hadir / total) * 100) : 0}
                  <span className="unit">%</span>
                </div>
                <div className="stat-hint">
                  {hadir} dari {total} pertemuan
                </div>
              </div>
            </div>
            <ul className="recap">
              {d.recap.map((r) => {
                const p = r.pertemuan ? (r.hadir / r.pertemuan) * 100 : 100;
                const tone = p < MIN_ATTENDANCE ? "bad" : p < MIN_ATTENDANCE + 5 ? "warn" : "ink";
                return (
                  <li key={r.kode}>
                    <div className="recap-head">
                      <span className="recap-name" title={r.course}>
                        {r.course}
                      </span>
                      <span className="mono">
                        {r.hadir}/{r.pertemuan} · {pct(p)}
                      </span>
                    </div>
                    <div className="meter" role="meter" aria-label={`Kehadiran ${r.course}`} aria-valuenow={Math.round(p)} aria-valuemin={0} aria-valuemax={100}>
                      <div className={`meter-fill ${tone}`} style={{ width: `${p}%` }} />
                    </div>
                  </li>
                );
              })}
            </ul>
          </>
        );
      }}
    </Panel>
  );
}
