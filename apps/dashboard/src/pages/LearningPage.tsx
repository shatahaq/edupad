import { usePanel } from "../api/usePanel";
import { PageIntro } from "../components/PageIntro";
import { CoursesLearnedPanel, LearningActivityPanel, MemoryPanel, SourcesPanel } from "../panels/LearningPanels";

export function LearningPage() {
  const data = usePanel("learning").data;
  const top = data?.courses[0];
  const active = data?.daily.filter((d) => d.questions > 0).length ?? 0;
  return (
    <>
      <PageIntro owl="metric" title="Riwayat belajar">
        {!data ? (
          "Memuat riwayat belajar…"
        ) : data.questions_total ? (
          <>
            {data.questions_total} pertanyaan dalam {data.window_days} hari, aktif {active} hari.
            {top && (
              <>
                {" "}
                Paling sering dibahas: <b>{top.course}</b>.
              </>
            )}
          </>
        ) : (
          "Belum ada pertanyaan dalam 30 hari terakhir."
        )}
      </PageIntro>
      <div className="grid-3-2">
        <LearningActivityPanel />
        <MemoryPanel />
      </div>
      <div className="grid-3-2">
        <CoursesLearnedPanel />
        <SourcesPanel />
      </div>
    </>
  );
}
