import { usePanel } from "../api/usePanel";
import { PageIntro } from "../components/PageIntro";
import { countdown } from "../lib/format";
import { TasksPanel } from "../panels/TasksPanel";

export function TasksPage() {
  const tasks = usePanel("assignments").data?.tasks;
  const pending = (tasks ?? []).filter((t) => !t.submitted && !t.overdue);
  const overdue = (tasks ?? []).filter((t) => !t.submitted && t.overdue).length;
  const nearest = pending.filter((t) => t.deadline).sort((a, b) => a.deadline!.localeCompare(b.deadline!))[0];

  return (
    <>
      <PageIntro owl="tempo" title="Tugas" mood={tasks && !pending.length && !overdue ? "happy" : "idle"} say={nearest ? "tugas apa yang deadline minggu ini?" : undefined}>
        {!tasks ? (
          "Memuat tugas dari kelas.usu dan Google Classroom…"
        ) : nearest ? (
          <>
            <b>{pending.length} tugas</b> belum dikumpulkan. Yang terdekat: <b>{nearest.judul}</b>, {countdown(nearest.deadline!)}.
            {overdue > 0 && <> {overdue} tugas sudah lewat deadline.</>}
          </>
        ) : overdue ? (
          <>
            Tidak ada deadline mendatang, tapi <b>{overdue} tugas</b> lewat deadline belum dikumpulkan.
          </>
        ) : (
          "Semua tugas sudah dikumpulkan. Kerja bagus!"
        )}
      </PageIntro>
      <TasksPanel />
    </>
  );
}
