import { PageHeader } from "../components/PageHeader";
import { AttendancePanel, AttendanceRecapPanel } from "../panels/AttendancePanel";

export function AttendancePage() {
  return (
    <>
      <PageHeader title="Presensi" subtitle="portal SATU" />
      <div className="row row-2-1">
        <AttendancePanel scope="week" />
        <AttendanceRecapPanel />
      </div>
    </>
  );
}
