import { usePanel } from "../api/usePanel";
import { PageIntro } from "../components/PageIntro";
import { hourLabel } from "../lib/format";
import { AttendancePanel, AttendanceRecapPanel } from "../panels/AttendancePanel";

export function AttendancePage() {
  const data = usePanel("attendance").data;
  const open = data?.today.filter((m) => m.window === "dibuka") ?? [];
  const next = data?.today.find((m) => m.window === "belum_dibuka");

  return (
    <>
      <PageIntro owl="tempo" title="Presensi" say={open.length ? undefined : "ada absen apa hari ini?"}>
        {!data ? (
          "Memuat presensi dari portal SATU…"
        ) : open.length ? (
          <>
            Presensi <b>{open[0].course}</b> sedang dibuka
            {open[0].selesai ? <> sampai <b>{hourLabel(open[0].selesai)}</b></> : null}. {open[0].cara.includes("QR") ? "Scan QR di kelas." : "Isi di portal SATU."}
          </>
        ) : next?.mulai ? (
          <>
            Belum ada yang dibuka. Berikutnya <b>{next.course}</b> pukul {hourLabel(next.mulai)}.
          </>
        ) : (
          "Tidak ada presensi lagi hari ini."
        )}
        {data?.stale && " Data SATU belum diperbarui beberapa jam terakhir."}
      </PageIntro>
      <div className="grid-3-2">
        <AttendancePanel scope="week" />
        <AttendanceRecapPanel />
      </div>
    </>
  );
}
