import { PageHeader } from "../components/PageHeader";
import { WeekSchedulePanel } from "../panels/SchedulePanels";

export function SchedulePage() {
  return (
    <>
      <PageHeader title="Jadwal kuliah" subtitle="portal SATU" />
      <WeekSchedulePanel />
    </>
  );
}
