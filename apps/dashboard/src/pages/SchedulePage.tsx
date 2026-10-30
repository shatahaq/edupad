import { usePanel } from "../api/usePanel";
import { PageIntro } from "../components/PageIntro";
import { classesToday, classState, WeekSchedulePanel } from "../panels/SchedulePanels";

const hm = (hhmm: string) => hhmm.replace(":", ".");

export function SchedulePage() {
  const schedule = usePanel("schedule").data;
  const today = schedule ? classesToday(schedule.classes) : [];
  const running = today.find((c) => classState(c) === "berlangsung");
  const next = today.find((c) => classState(c) === "nanti");

  return (
    <>
      <PageIntro owl="tempo" title="Jadwal" say="kuliah besok apa?">
        {!schedule ? (
          "Memuat jadwal…"
        ) : running ? (
          <>
            Sekarang <b>{running.course}</b> di {running.nama_ruang || running.ruang}, sampai {hm(running.selesai)}.
          </>
        ) : next ? (
          <>
            Berikutnya <b>{next.course}</b> pukul {hm(next.mulai)} di {next.nama_ruang || next.ruang}.
          </>
        ) : today.length ? (
          "Kuliah hari ini sudah selesai."
        ) : (
          "Tidak ada kuliah hari ini."
        )}
      </PageIntro>
      <WeekSchedulePanel />
    </>
  );
}
