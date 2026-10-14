import { PageHeader } from "../components/PageHeader";
import { CoursesLearnedPanel, LearningActivityPanel, MemoryPanel, SourcesPanel } from "../panels/LearningPanels";

export function LearningPage() {
  return (
    <>
      <PageHeader title="Riwayat belajar" subtitle="30 hari terakhir" />
      <div className="row row-2-1">
        <LearningActivityPanel />
        <MemoryPanel />
      </div>
      <div className="row row-2-1">
        <CoursesLearnedPanel />
        <SourcesPanel />
      </div>
    </>
  );
}
