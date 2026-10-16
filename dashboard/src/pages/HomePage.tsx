import type { ClassSlot, FinanceData, Task, Weekday } from "../api/types";
import { usePanel } from "../api/usePanel";
import { PageIntro } from "../components/PageIntro";
import { Bar, Section } from "../components/Section";
import { countdown, dayLabel, hourLabel } from "../lib/format";
import { go } from "../lib/router";
import { useViewer } from "../lib/session";
import { classState, todayWeekday } from "../panels/SchedulePanels";

const DAY_MS = 86_400_000;
const WEEK: Weekday[] = ["senin", "selasa", "rabu", "kamis", "jumat", "sabtu", "minggu"];
const DAY_LABEL: Record<Weekday, string> = { senin: "Senin", selasa: "Selasa", rabu: "Rabu", kamis: "Kamis", jumat: "Jumat", sabtu: "Sabtu", minggu: "Minggu" };
const money = new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 });
const hm = (hhmm: string) => hhmm.replace(":", ".");

function greeting() {
  const hour = Number(hourLabel(new Date().toISOString()).split(".")[0]);
  if (hour < 4) return "Selamat malam";
  if (hour < 11) return "Selamat pagi";
  if (hour < 15) return "Selamat siang";
  if (hour < 19) return "Selamat sore";
  return "Selamat malam";
}

/** Kelas yang sedang berlangsung, atau berikutnya dalam seminggu ke depan. */
function upcomingClass(classes: ClassSlot[]): { slot: ClassSlot; day: string; now: boolean } | null {
  const today = todayWeekday();
  const start = WEEK.indexOf(today);
  for (let offset = 0; offset < 7; offset++) {
    const day = WEEK[(start + offset) % 7];
    const list = classes.filter((c) => c.hari === day).sort((a, b) => a.mulai.localeCompare(b.mulai));
    for (const slot of list) {
      if (offset === 0) {
        const state = classState(slot);
        if (state === "selesai") continue;
        return { slot, day: "Hari ini", now: state === "berlangsung" };
      }
      return { slot, day: offset === 1 ? "Besok" : DAY_LABEL[day], now: false };
    }
  }
  return null;
}

const pendingTasks = (tasks: Task[]) =>
  tasks.filter((t) => !t.submitted && !t.overdue && t.deadline).sort((a, b) => a.deadline!.localeCompare(b.deadline!));

export function HomePage() {
  const viewer = useViewer();
  const attendance = usePanel("attendance").data;
  const tasks = usePanel("assignments").data?.tasks;
  const schedule = usePanel("schedule").data;
  const tutor = usePanel("tutor").data;
  const finance = usePanel("finance").data;
  const equity = usePanel("equity").data;
  const conversations = usePanel("conversations").data;

  const openPresence = attendance?.today.filter((m) => m.window === "dibuka") ?? [];
  const pending = tasks ? pendingTasks(tasks) : [];
  const soon = pending.filter((t) => new Date(t.deadline!).getTime() - Date.now() < 3 * DAY_MS);
  const overdue = tasks?.filter((t) => !t.submitted && t.overdue).length ?? 0;
  const next = schedule ? upcomingClass(schedule.classes) : null;
  const help = tutor?.help?.find((h) => h.status === "siap" || h.status === "berjalan");
  const due = tutor?.topics.filter((t) => t.jatuh_tempo) ?? [];
  const warnings = equity?.warnings.filter((w) => w.jenis !== "tugas_terlewat") ?? [];

  const firstName = (viewer?.name ?? "").split(" ")[0];
  const loaded = Boolean(attendance && tasks && tutor);
  const serious = warnings.filter((w) => w.tingkat === "tinggi").length;
  const urgent = [
    openPresence.length && `${openPresence.length} presensi sedang dibuka`,
    soon.length && `${soon.length} tugas deadline dalam 3 hari`,
    overdue && `${overdue} tugas lewat deadline belum dikumpulkan`,
    serious && `${serious} peringatan penting`,
    help && "SORA menyiapkan bantuan belajar",
  ].filter(Boolean) as string[];

  return (
    <>
      <PageIntro owl="nova" title={`${greeting()}${firstName ? `, ${firstName}` : ""}`} mood={loaded && !urgent.length ? "happy" : "idle"}>
        {!loaded ? (
          "Menyiapkan ringkasan hari ini…"
        ) : urgent.length ? (
          <>
            Hari ini: <b>{urgent.join(", ")}</b>.
          </>
        ) : (
          "Tidak ada yang mendesak hari ini. Saat yang pas untuk mengulang materi."
        )}
      </PageIntro>

      <div className="grid-3-2">
        <div className="column">
          <Section title={next?.now ? "Sedang berlangsung" : "Kuliah berikutnya"} strong={openPresence.length > 0}>
            {openPresence.map((m) => (
              <div key={m.id} className="presence-open">
                <span className="tag good">Presensi dibuka</span>
                <strong>{m.course}</strong>
                <span>
                  {m.selesai ? `Tutup ${hourLabel(m.selesai)} · ${countdown(m.selesai)}` : "Sedang dibuka"} ·{" "}
                  {m.cara.includes("QR") ? "scan QR di kelas" : "isi di portal SATU"}
                </span>
              </div>
            ))}
            {next ? (
              <div className="next-class">
                <div className="when">
                  <b>{hm(next.slot.mulai)}</b>
                  <span>{next.day}</span>
                </div>
                <div className="item-main">
                  <strong>{next.slot.course}</strong>
                  <span>
                    {next.slot.nama_ruang || next.slot.ruang} · sampai {hm(next.slot.selesai)}
                  </span>
                </div>
              </div>
            ) : (
              <p className="empty-line">{schedule ? "Tidak ada jadwal kuliah minggu ini." : "Memuat jadwal…"}</p>
            )}
          </Section>

          <Section
            title="Tugas terdekat"
            note={overdue ? <span className="bad-text">{overdue} tugas sudah lewat deadline</span> : undefined}
            action={
              <button className="section-link" onClick={() => go("tugas")}>
                Semua tugas
              </button>
            }
          >
            {pending.length ? (
              <ul className="list">
                {pending.slice(0, 4).map((t) => {
                  const near = new Date(t.deadline!).getTime() - Date.now() < DAY_MS;
                  return (
                    <li key={`${t.sumber}-${t.id}`}>
                      <div className="when">
                        <b>{dayLabel(t.deadline!)}</b>
                        <span>{hourLabel(t.deadline!)}</span>
                      </div>
                      <div className="item-main">
                        <strong>{t.judul}</strong>
                        <span>{t.course}</span>
                      </div>
                      <span className={`tag ${near ? "bad" : ""}`}>{countdown(t.deadline!)}</span>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="empty-line">{tasks ? "Tidak ada tugas yang menunggu." : "Memuat tugas…"}</p>
            )}
          </Section>

          <RecentQuestions sessions={conversations?.sessions} />
        </div>

        <div className="column">
          <Section title="Dari SORA" action={<button className="section-link" onClick={() => go("tutor")}>Tutor</button>}>
            {help ? (
              <div className="tip">
                <strong>{help.judul}</strong>
                <span>{help.masalah || help.alasan.join(", ")}</span>
                <p className="say-hint">
                  Ucapkan ke EduPad: <q>mulai</q>
                </p>
              </div>
            ) : due.length ? (
              <div className="tip">
                <strong>Waktunya mengulang {due[0].judul || due[0].matkul}</strong>
                <span>Penguasaan {due[0].penguasaan}%</span>
                <p className="say-hint">
                  Ucapkan ke EduPad: <q>uji aku lagi</q>
                </p>
              </div>
            ) : (
              <div className="tip">
                <span>Belum ada topik yang perlu diulang.</span>
                <p className="say-hint">
                  Coba ucapkan: <q>uji aku Basis Data pertemuan dua</q>
                </p>
              </div>
            )}
          </Section>

          <MoneySection finance={finance} />

          {warnings.length > 0 && (
            <Section title="Perlu perhatian">
              <ul className="list">
                {warnings.slice(0, 3).map((w) => (
                  <li key={w.kunci}>
                    <span className={`tag ${w.tingkat === "tinggi" ? "bad" : "warn"}`}>{w.jenis === "anggaran" ? "Uang" : "Hadir"}</span>
                    <div className="item-main">
                      <span className="item-text">{w.pesan}</span>
                    </div>
                  </li>
                ))}
              </ul>
            </Section>
          )}
        </div>
      </div>
    </>
  );
}

function MoneySection({ finance }: { finance: FinanceData | null }) {
  if (!finance?.available) return null;
  const month = new Date().toISOString().slice(0, 7);
  const spent = finance.transactions
    .filter((t) => t.kind === "expense" && String(t.occurred_on).startsWith(month))
    .reduce((total, t) => total + Number(t.amount), 0);
  const budget = Object.values(finance.budgets).reduce((total, v) => total + v, 0);
  const ratio = budget ? (spent / budget) * 100 : 0;
  return (
    <Section title="Uang bulan ini" action={<button className="section-link" onClick={() => go("keuangan")}>Keuangan</button>}>
      <div className="money">
        <b>{budget ? money.format(budget - spent) : money.format(spent)}</b>
        <span>{budget ? `sisa dari anggaran ${money.format(budget)}` : "pengeluaran bulan ini"}</span>
      </div>
      {budget > 0 && <Bar value={ratio} tone={ratio >= 100 ? "bad" : ratio >= 90 ? "warn" : "good"} label="Anggaran terpakai" />}
      <p className="say-hint">
        Catat lewat suara: <q>tadi beli makan dua puluh lima ribu</q>
      </p>
    </Section>
  );
}

function RecentQuestions({ sessions }: { sessions?: { turns: { id: unknown; at: string | null; question: string; speech: string }[] }[] }) {
  const turns = (sessions ?? [])
    .flatMap((s) => s.turns)
    .filter((t) => t.question)
    .sort((a, b) => String(b.at).localeCompare(String(a.at)))
    .slice(0, 3);
  return (
    <Section
      title="Terakhir ditanyakan"
      action={
        <button className="section-link" onClick={() => go("percakapan")}>
          Semua percakapan
        </button>
      }
    >
      {turns.length ? (
        <ul className="list">
          {turns.map((t) => (
            <li key={String(t.id)}>
              <div className="item-main">
                <strong>“{t.question}”</strong>
                <span className="clamp-2">{t.speech}</span>
              </div>
              <span className="item-meta">{t.at ? dayLabel(t.at) : ""}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="empty-line">{sessions ? "Belum ada pertanyaan lewat perangkat." : "Memuat…"}</p>
      )}
    </Section>
  );
}
