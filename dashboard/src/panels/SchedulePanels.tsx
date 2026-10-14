import type { ClassSlot, Weekday } from "../api/types";
import { Panel } from "../components/Panel";
import { Icon } from "../components/Icon";
import { countdown, hourLabel, wibDate } from "../lib/format";

const ORDER: Weekday[] = ["senin", "selasa", "rabu", "kamis", "jumat", "sabtu", "minggu"];
const LABEL: Record<Weekday, string> = { senin: "Senin", selasa: "Selasa", rabu: "Rabu", kamis: "Kamis", jumat: "Jumat", sabtu: "Sabtu", minggu: "Minggu" };

/** Hari ini (WIB) sebagai Weekday. */
export function todayWeekday(): Weekday {
  // 2024-01-01 adalah Senin; selisih hari dari tanggal itu menentukan nama hari tanpa bergantung locale.
  const days = Math.round((Date.parse(wibDate(Date.now())) - Date.parse("2024-01-01")) / 86_400_000);
  return ORDER[((days % 7) + 7) % 7];
}

/** "HH:MM" WIB hari ini -> ISO, untuk countdown. */
const todayAt = (hhmm: string) => new Date(`${wibDate(Date.now())}T${hhmm}:00+07:00`).toISOString();

export type ClassState = "selesai" | "berlangsung" | "nanti";

export function classState(c: ClassSlot): ClassState {
  const nowHHMM = hourLabel(new Date().toISOString()).replace(".", ":");
  return nowHHMM >= c.selesai ? "selesai" : nowHHMM >= c.mulai ? "berlangsung" : "nanti";
}

export function classesToday(classes: ClassSlot[]) {
  const day = todayWeekday();
  return classes.filter((c) => c.hari === day).sort((a, b) => a.mulai.localeCompare(b.mulai));
}

const hm = (hhmm: string) => hhmm.replace(":", ".");

export function TodaySchedulePanel() {
  return (
    <Panel panel="schedule" title="Jadwal hari ini" subtitle="Kelas dan ruangan">
      {(d) => {
        const list = classesToday(d.classes);
        if (!list.length) return <p className="empty">Tidak ada kelas hari ini.</p>;
        return (
          <ol className="timeline">
            {list.map((c) => {
              const state = classState(c);
              return (
                <li key={`${c.kode}-${c.mulai}`} className={state}>
                  <div className="slot-time mono">
                    {hm(c.mulai)}
                    <span>{hm(c.selesai)}</span>
                  </div>
                  <div className="row-main">
                    <div className="cell-strong wrap">{c.course}</div>
                    <div className="cell-sub wrap">
                      {c.nama_ruang} · {c.ruang}
                    </div>
                  </div>
                  <div className="row-side">
                    {state === "berlangsung" ? (
                      <span className="pill good">Berlangsung</span>
                    ) : state === "selesai" ? (
                      <span className="cell-sub">selesai</span>
                    ) : (
                      <span className="cell-sub mono">{countdown(todayAt(c.mulai))}</span>
                    )}
                  </div>
                </li>
              );
            })}
          </ol>
        );
      }}
    </Panel>
  );
}

export function WeekSchedulePanel() {
  return (
    <Panel panel="schedule" title="Jadwal mingguan" subtitle="Semester berjalan · WIB">
      {(d) => {
        const today = todayWeekday();
        // Senin–Jumat selalu tampil; Sabtu/Minggu hanya bila ada kelas.
        const days = ORDER.filter((day) => ORDER.indexOf(day) < 5 || d.classes.some((c) => c.hari === day));
        return (
          <div className="week" style={{ ["--days" as string]: days.length }}>
            {days.map((day) => {
              const list = d.classes.filter((c) => c.hari === day).sort((a, b) => a.mulai.localeCompare(b.mulai));
              return (
                <section key={day} className={`week-day ${day === today ? "today" : ""}`} aria-label={LABEL[day]}>
                  <header>
                    <span>{LABEL[day]}</span>
                    {day === today && <span className="pill">Hari ini</span>}
                  </header>
                  {list.length ? (
                    list.map((c) => (
                      <article key={`${c.kode}-${c.mulai}`} className={`class-card ${day === today ? classState(c) : ""}`}>
                        <div className="mono class-time">
                          {hm(c.mulai)}–{hm(c.selesai)}
                        </div>
                        <div className="cell-strong wrap">{c.course}</div>
                        <div className="cell-sub wrap">
                          <Icon name="pin" size={11} /> {c.nama_ruang} · {c.ruang}
                        </div>
                        <div className="cell-sub wrap">{c.dosen.join(", ")}</div>
                        <div className="class-tags">
                          <span className="pill">{c.jenis}</span>
                          <span className="pill">
                            <b>{c.sks}</b> sks
                          </span>
                          <span className="pill">{c.kelas}</span>
                        </div>
                      </article>
                    ))
                  ) : (
                    <p className="empty">Tidak ada kelas</p>
                  )}
                </section>
              );
            })}
          </div>
        );
      }}
    </Panel>
  );
}
