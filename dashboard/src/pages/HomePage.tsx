import { usePanel } from "../api/usePanel";
import { DASH, Kpi } from "../components/KpiRow";
import { PageHeader } from "../components/PageHeader";
import { countdown, hourLabel, num } from "../lib/format";
import { AttendancePanel } from "../panels/AttendancePanel";
import { RecentTurnsPanel } from "../panels/ConversationPanels";
import { classesToday, classState, TodaySchedulePanel } from "../panels/SchedulePanels";
import { UpcomingTasksPanel } from "../panels/TasksPanel";

const DAY_MS = 86_400_000;
const todayLong = new Intl.DateTimeFormat("id-ID", { weekday: "long", day: "numeric", month: "long", timeZone: "Asia/Jakarta" });

/** Empat angka "hari ini" dari data presensi, tugas, jadwal, dan riwayat belajar. */
function TodayKpis() {
  const att = usePanel("attendance").data;
  const tasks = usePanel("assignments").data?.tasks;
  const schedule = usePanel("schedule").data;
  const learning = usePanel("learning").data;

  const open = att?.today.filter((m) => m.window === "dibuka") ?? [];
  const nextOpen = att?.today.find((m) => m.window === "belum_dibuka");

  const pending = (tasks ?? []).filter((t) => !t.submitted && !t.overdue);
  const overdue = (tasks ?? []).filter((t) => !t.submitted && t.overdue).length;
  const nearest = pending.filter((t) => t.deadline).sort((a, b) => a.deadline!.localeCompare(b.deadline!))[0];
  const nearestUrgent = nearest && new Date(nearest.deadline!).getTime() - Date.now() < DAY_MS;

  const classes = schedule ? classesToday(schedule.classes) : [];
  const running = classes.find((c) => classState(c) === "berlangsung");
  const nextClass = classes.find((c) => classState(c) === "nanti");

  const recent = learning?.daily.slice(-14) ?? [];
  const todayQuestions = recent[recent.length - 1]?.questions ?? 0;

  return (
    <section className="kpis" aria-label="Ringkasan hari ini">
      <Kpi
        label="Presensi dibuka"
        value={att ? open.length : DASH}
        unit={att ? `dari ${att.today.length}` : undefined}
        foot={
          !att ? (
            DASH
          ) : open[0] ? (
            <>
              tutup <b>{hourLabel(open[0].selesai!)}</b> · <span className="bad-text">{countdown(open[0].selesai!)}</span>
              <span className="sep">·</span>
              {open[0].course}
            </>
          ) : nextOpen?.mulai ? (
            <>
              berikutnya <span className="name">{nextOpen.course}</span> {hourLabel(nextOpen.mulai)}
            </>
          ) : (
            "tidak ada lagi hari ini"
          )
        }
      />
      <Kpi
        label="Tugas belum dikumpulkan"
        value={tasks ? pending.length : DASH}
        foot={
          !tasks ? (
            DASH
          ) : (
            <>
              {nearest ? (
                <>
                  terdekat <b className={nearestUrgent ? "bad-text" : undefined}>{countdown(nearest.deadline!)}</b>
                </>
              ) : (
                "tidak ada deadline"
              )}
              {overdue > 0 && (
                <>
                  <span className="sep">·</span>
                  <span className="bad-text">{overdue} lewat</span>
                </>
              )}
            </>
          )
        }
      />
      <Kpi
        label="Kelas hari ini"
        value={schedule ? classes.length : DASH}
        foot={
          !schedule ? (
            DASH
          ) : running ? (
            <>
              sedang <span className="name">{running.course}</span>
            </>
          ) : nextClass ? (
            <>
              berikutnya <span className="name">{nextClass.course}</span> {nextClass.mulai.replace(":", ".")}
            </>
          ) : classes.length ? (
            "semua selesai"
          ) : (
            "libur"
          )
        }
      />
      <Kpi
        label="Pertanyaan ke EduPad"
        value={learning ? todayQuestions : DASH}
        unit={learning ? "hari ini" : undefined}
        bars={recent.map((d) => d.questions)}
        barsLabel="Pertanyaan per hari, 14 hari terakhir"
        foot={
          learning ? (
            <>
              <b>{num(learning.questions_total)}</b> dalam {learning.window_days} hari
            </>
          ) : (
            DASH
          )
        }
      />
    </section>
  );
}

export function HomePage() {
  return (
    <>
      <PageHeader title="Hari ini" subtitle={todayLong.format(new Date())} />
      <TodayKpis />
      <div className="row row-2-1">
        <AttendancePanel scope="today" />
        <TodaySchedulePanel />
      </div>
      <div className="row row-2-1">
        <UpcomingTasksPanel />
        <RecentTurnsPanel />
      </div>
    </>
  );
}
