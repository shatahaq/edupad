import { PageHeader } from "../components/PageHeader";
import { TasksPanel } from "../panels/TasksPanel";

export function TasksPage() {
  return (
    <>
      <PageHeader title="Tugas & deadline" subtitle="kelas.usu.ac.id" />
      <TasksPanel />
    </>
  );
}
