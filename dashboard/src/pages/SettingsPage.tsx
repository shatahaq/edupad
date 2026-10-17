import { type FormEvent, useEffect, useState } from "react";
import { apiSend } from "../api/client";
import type { VoiceSpeed } from "../api/types";
import { usePanel } from "../api/usePanel";
import { PageHeader } from "../components/PageHeader";
import { FINANCE_BUDGETS_KEY, FINANCE_TRANSACTIONS_KEY, loadFinanceBudgets, loadFinanceTransactions } from "../lib/finance";
import { loadPreferences, savePreferences, type DashboardPreferences } from "../lib/preferences";
import { SPEED_LABEL } from "../lib/voice";

export function SettingsPage() {
  const [draft, setDraft] = useState<DashboardPreferences>(loadPreferences);
  const [saved, setSaved] = useState(false);
  const [financeStorage, setFinanceStorage] = useState(() => {
    const transactionCount = loadFinanceTransactions().length;
    const hasBudget = Object.values(loadFinanceBudgets()).some((value) => value > 0);
    return { transactionCount, hasData: transactionCount > 0 || hasBudget };
  });

  const submit = (event: FormEvent) => {
    event.preventDefault();
    savePreferences({ ...draft, studentName: draft.studentName.trim() || "Mahasiswa", studentId: draft.studentId.trim() });
    setSaved(true);
    window.setTimeout(() => setSaved(false), 2200);
  };

  const clearFinance = () => {
    if (!window.confirm("Hapus salinan lama keuangan di browser ini? Data di server EduPad tidak ikut terhapus.")) return;
    localStorage.removeItem(FINANCE_TRANSACTIONS_KEY);
    localStorage.removeItem(FINANCE_BUDGETS_KEY);
    setFinanceStorage({ transactionCount: 0, hasData: false });
  };

  return (
    <div className="settings-page">
      <PageHeader title="Pengaturan" subtitle="Nama tampilan dan kenyamanan tampilan dashboard." />
      <form className="settings-grid" onSubmit={submit}>
        <VoiceModeSection />

        <section className="card settings-panel">
          <div className="settings-panel-head"><div><h2>Profil mahasiswa</h2><p>Nama ini tampil pada bagian bawah menu utama.</p></div></div>
          <div className="settings-fields">
            <label><span>Nama tampilan</span><input value={draft.studentName} onChange={(event) => setDraft((current) => ({ ...current, studentName: event.target.value }))} placeholder="Nama mahasiswa" maxLength={60} /></label>
            <label><span>NIM <small>(opsional)</small></span><input value={draft.studentId} onChange={(event) => setDraft((current) => ({ ...current, studentId: event.target.value }))} placeholder="Nomor induk mahasiswa" maxLength={30} /></label>
          </div>
        </section>

        <section className="card settings-panel">
          <div className="settings-panel-head"><div><h2>Tampilan</h2><p>Sesuaikan kepadatan dan gerakan antarmuka.</p></div></div>
          <div className="settings-toggles">
            <label><div><strong>Mode ringkas</strong><span>Mengurangi jarak antarkomponen agar lebih banyak informasi terlihat.</span></div><input type="checkbox" checked={draft.compactMode} onChange={(event) => setDraft((current) => ({ ...current, compactMode: event.target.checked }))} /></label>
            <label><div><strong>Kurangi animasi</strong><span>Mengurangi transisi dashboard dan animasi dekoratif.</span></div><input type="checkbox" checked={draft.reduceMotion} onChange={(event) => setDraft((current) => ({ ...current, reduceMotion: event.target.checked }))} /></label>
          </div>
        </section>


        {financeStorage.hasData && <section className="card settings-panel">
          <div className="settings-panel-head"><div><h2>Salinan lama di browser</h2><p>Keuangan kini tersimpan di server EduPad (Supabase) dan sinkron dengan perangkat. Salinan lama hanya tersisa bila belum dipindahkan dari halaman Keuangan.</p></div></div>
          <div className="settings-data-row"><div><strong>{financeStorage.transactionCount} transaksi di browser ini</strong><span>{financeStorage.hasData ? "Pindahkan dari halaman Keuangan sebelum menghapus." : "Tidak ada salinan lama."}</span></div><button type="button" className="btn settings-danger" disabled={!financeStorage.hasData} onClick={clearFinance}>Hapus salinan lama</button></div>
        </section>}

        <div className="settings-savebar"><span className={saved ? "visible" : ""}><i />Pengaturan berhasil disimpan</span><button type="submit" className="btn btn-dark">Simpan pengaturan</button></div>
      </form>
    </div>
  );
}

/** Mode Suara (server, src/edupad/voice/mode.py): tersimpan langsung, tanpa tombol Simpan. */
function VoiceModeSection() {
  const panel = usePanel("voice");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  // Pilihan langsung tampil saat diklik; dikembalikan bila server menolak.
  const [pending, setPending] = useState<{ enabled?: boolean; speed?: VoiceSpeed }>({});
  useEffect(() => setPending({}), [panel.data]);
  const data = panel.data && { ...panel.data, ...pending };

  const change = async (body: { enabled?: boolean; speed?: VoiceSpeed }) => {
    setBusy(true);
    setError("");
    setPending((current) => ({ ...current, ...body }));
    try {
      await apiSend("PUT", "/api/office/voice-mode", body);
      panel.reload();
    } catch (e) {
      setPending({});
      setError(e instanceof Error ? e.message : "Mode Suara gagal disimpan.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card settings-panel">
      <div className="settings-panel-head">
        <div>
          <h2>Mode Suara</h2>
          <p>
            Untuk mahasiswa tunanetra: semua jawaban dan pemberitahuan dibacakan, ada bunyi penanda saat mulai merekam. Tersimpan
            langsung; bisa juga lewat suara, “aktifkan mode suara”.
          </p>
        </div>
      </div>
      {data ? (
        <div className="settings-toggles">
          <label>
            <div>
              <strong>Aktifkan Mode Suara</strong>
              <span>Bunyi penanda dan pemberitahuan bersuara butuh firmware perangkat 1.2.</span>
            </div>
            <input type="checkbox" checked={data.enabled} disabled={busy} onChange={(event) => change({ enabled: event.target.checked })} />
          </label>
          <label>
            <div>
              <strong>Kecepatan bicara</strong>
              <span>Berlaku untuk semua jawaban. Pengguna pembaca layar biasanya nyaman dengan yang lebih cepat.</span>
            </div>
            <select className="curve-select" value={data.speed} disabled={busy} onChange={(event) => change({ speed: event.target.value as VoiceSpeed })}>
              {data.speeds.map((speed) => (
                <option key={speed} value={speed}>
                  {SPEED_LABEL[speed]}
                </option>
              ))}
            </select>
          </label>
        </div>
      ) : (
        <p className="empty-line">{panel.error ? `Belum bisa dimuat: ${panel.error}` : "Memuat…"}</p>
      )}
      {error && (
        <div className="panel-error" role="alert">
          {error}
        </div>
      )}
    </section>
  );
}
