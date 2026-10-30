import { type FormEvent, useEffect, useMemo, useState } from "react";
import { apiSend } from "../api/client";
import type { FinanceRow } from "../api/types";
import { usePanel } from "../api/usePanel";
import { Icon } from "../components/Icon";
import { PageIntro } from "../components/PageIntro";
import {
  clearLegacyFinance,
  loadFinanceBudgets,
  loadFinanceTransactions,
  type FinanceBudgets,
  type FinanceKind,
  type FinanceTransaction,
} from "../lib/finance";

const EXPENSE_CATEGORIES = ["Makan", "Transportasi", "Tempat tinggal", "Kuliah", "Internet", "Kesehatan", "Hiburan", "Lainnya"];
const INCOME_CATEGORIES = ["Kiriman keluarga", "Beasiswa", "Kerja sampingan", "Pengembalian", "Lainnya"];

/** Baris Supabase -> bentuk yang dipakai tampilan. */
function toView(row: FinanceRow): FinanceTransaction {
  return {
    id: row.id,
    kind: row.kind,
    amount: Number(row.amount),
    category: row.category,
    date: String(row.occurred_on).slice(0, 10),
    note: row.note,
    createdAt: row.created_at,
    source: row.source,
  };
}
const TABS = [
  ["summary", "Ringkasan"],
  ["transactions", "Transaksi"],
  ["budgets", "Anggaran"],
  ["reports", "Laporan"],
] as const;

type FinanceTab = (typeof TABS)[number][0];

const money = new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 });
const compactMoney = new Intl.NumberFormat("id-ID", { notation: "compact", maximumFractionDigits: 1 });
const monthLabel = new Intl.DateTimeFormat("id-ID", { month: "long", year: "numeric" });
const dateLabel = new Intl.DateTimeFormat("id-ID", { day: "2-digit", month: "short", year: "numeric" });

function localDate() {
  const date = new Date();
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 10);
}

function formatMonth(value: string) {
  const [year, month] = value.split("-").map(Number);
  return monthLabel.format(new Date(year, month - 1, 1));
}

function downloadCsv(rows: FinanceTransaction[], month: string) {
  const escape = (value: string | number) => `"${String(value).replace(/"/g, '""')}"`;
  const lines = [
    ["Tanggal", "Jenis", "Kategori", "Catatan", "Nominal"].map(escape).join(","),
    ...rows.map((row) => [row.date, row.kind === "income" ? "Pemasukan" : "Pengeluaran", row.category, row.note, row.amount].map(escape).join(",")),
  ];
  const blob = new Blob(["\uFEFF" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `laporan-keuangan-${month}.csv`;
  anchor.click();
  URL.revokeObjectURL(url);
}

function Metric({ label, value, hint, tone }: { label: string; value: string; hint: string; tone?: string }) {
  return (
    <article className={`finance-metric card ${tone ?? ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{hint}</small>
    </article>
  );
}

export function FinancePage() {
  const panel = usePanel("finance");
  const available = panel.data?.available ?? false;
  const transactions = useMemo(() => (panel.data?.transactions ?? []).map(toView), [panel.data]);
  const savedBudgets: FinanceBudgets = panel.data?.budgets ?? {};
  const [budgets, setBudgets] = useState<FinanceBudgets>({});
  const [busy, setBusy] = useState(false);
  const [legacy, setLegacy] = useState(() => ({ rows: loadFinanceTransactions(), budgets: loadFinanceBudgets() }));
  const legacyCount = legacy.rows.length + Object.values(legacy.budgets).filter((value) => value > 0).length;
  const [tab, setTab] = useState<FinanceTab>("summary");
  const [month, setMonth] = useState(localDate().slice(0, 7));
  const [composer, setComposer] = useState(false);
  const [kind, setKind] = useState<FinanceKind>("expense");
  const [amount, setAmount] = useState("");
  const [category, setCategory] = useState(EXPENSE_CATEGORIES[0]);
  const [date, setDate] = useState(localDate());
  const [note, setNote] = useState("");
  const [error, setError] = useState("");

  // Draf anggaran mengikuti server; perubahan disimpan saat kolom ditinggalkan. Disinkronkan
  // hanya bila nilai di server berubah, agar refresh berkala tidak menimpa angka yang sedang diketik.
  const savedKey = JSON.stringify(savedBudgets);
  useEffect(() => setBudgets(JSON.parse(savedKey) as FinanceBudgets), [savedKey]);

  const saveBudget = async (name: string) => {
    const value = budgets[name] ?? 0;
    if (value === (savedBudgets[name] ?? 0)) return;
    try {
      await apiSend("PUT", `/api/office/finance/budgets/${encodeURIComponent(name)}`, { amount: value });
      panel.reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Anggaran gagal disimpan.");
    }
  };

  const removeTransaction = async (row: FinanceTransaction) => {
    if (!window.confirm(`Hapus transaksi ${row.note || row.category} (${money.format(row.amount)})?`)) return;
    try {
      await apiSend("DELETE", `/api/office/finance/transactions/${encodeURIComponent(row.id)}`);
      panel.reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Transaksi gagal dihapus.");
    }
  };

  const importLegacy = async () => {
    setBusy(true);
    try {
      await apiSend("POST", "/api/office/finance/import", {
        transactions: legacy.rows.map((row) => ({ kind: row.kind, amount: row.amount, category: row.category, note: row.note, date: row.date })),
        budgets: Object.fromEntries(Object.entries(legacy.budgets).filter(([, value]) => value > 0)),
      });
      clearLegacyFinance();
      setLegacy({ rows: [], budgets: {} });
      panel.reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Data lama gagal dipindahkan.");
    } finally {
      setBusy(false);
    }
  };

  const monthRows = useMemo(
    () => transactions.filter((row) => row.date.startsWith(month)).sort((a, b) => b.date.localeCompare(a.date) || b.createdAt.localeCompare(a.createdAt)),
    [transactions, month],
  );
  const income = monthRows.filter((row) => row.kind === "income").reduce((total, row) => total + row.amount, 0);
  const expense = monthRows.filter((row) => row.kind === "expense").reduce((total, row) => total + row.amount, 0);
  const balance = income - expense;
  const budgetTotal = Object.values(budgets).reduce((total, value) => total + value, 0);
  const remainingBudget = budgetTotal - expense;
  const savingsRate = income > 0 ? (balance / income) * 100 : 0;

  const spendingByCategory = EXPENSE_CATEGORIES.map((name) => ({
    name,
    amount: monthRows.filter((row) => row.kind === "expense" && row.category === name).reduce((total, row) => total + row.amount, 0),
    budget: budgets[name] ?? 0,
  })).filter((row) => row.amount || row.budget);
  const maxCategory = Math.max(1, ...spendingByCategory.map((row) => Math.max(row.amount, row.budget)));

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const numericAmount = Number(amount.replace(/[^0-9]/g, ""));
    if (!numericAmount || numericAmount < 1) {
      setError("Masukkan nominal yang lebih besar dari Rp0.");
      return;
    }
    if (!date) {
      setError("Pilih tanggal transaksi.");
      return;
    }
    setBusy(true);
    try {
      await apiSend("POST", "/api/office/finance/transactions", { kind, amount: numericAmount, category, date, note: note.trim() });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Transaksi gagal disimpan.");
      return;
    } finally {
      setBusy(false);
    }
    panel.reload();
    setAmount("");
    setNote("");
    setError("");
    setComposer(false);
    setMonth(date.slice(0, 7));
  };

  const changeKind = (next: FinanceKind) => {
    setKind(next);
    setCategory((next === "expense" ? EXPENSE_CATEGORIES : INCOME_CATEGORIES)[0]);
  };

  return (
    <div className="finance-page">
      <PageIntro
        owl="koin"
        title="Keuangan"
        say="tadi beli makan dua puluh lima ribu"
        actions={
          <button className="btn btn-dark" disabled={!available} onClick={() => setComposer((open) => !open)}>
            {composer ? "Tutup formulir" : "Catat transaksi"}
          </button>
        }
      >
        {!panel.data ? (
          "Memuat catatan keuangan…"
        ) : budgetTotal ? (
          <>
            Sisa anggaran bulan ini <b>{money.format(remainingBudget)}</b> dari {money.format(budgetTotal)}.
          </>
        ) : (
          <>
            Pengeluaran bulan ini <b>{money.format(expense)}</b>. Atur anggaran supaya aku bisa mengingatkan sebelum habis.
          </>
        )}
      </PageIntro>

      {panel.data && !available && (
        <div className="panel-error" role="alert">Keuangan belum aktif di server: {panel.data.reason}</div>
      )}
      {panel.error && <div className="panel-error" role="alert">Data keuangan belum bisa dimuat: {panel.error}</div>}
      {error && !composer && <div className="panel-error" role="alert">{error}</div>}


      {available && legacyCount > 0 && (
        <section className="finance-voice card warn" aria-label="Pindahkan data lama">
          <Icon name="database" size={18} />
          <div>
            <strong>{legacy.rows.length} transaksi lama masih tersimpan di browser ini</strong>
            <p>Pindahkan sekali ke server agar terlihat dari perangkat lain dan bisa dibaca AI EduPad.</p>
          </div>
          <button className="btn btn-dark" disabled={busy} onClick={importLegacy}>
            {busy ? "Memindahkan…" : "Pindahkan ke server"}
          </button>
        </section>
      )}

      <section className="finance-toolbar card" aria-label="Periode dan bagian keuangan">
        <div className="finance-tabs" role="tablist" aria-label="Bagian keuangan">
          {TABS.map(([id, label]) => <button key={id} role="tab" aria-selected={tab === id} className={tab === id ? "active" : ""} onClick={() => setTab(id)}>{label}</button>)}
        </div>
        <label className="finance-month"><span>Periode</span><input type="month" value={month} onChange={(event) => setMonth(event.target.value)} /></label>
      </section>

      {composer && (
        <section className="finance-composer card">
          <div className="finance-section-head"><div><h2>Catat perubahan uang</h2><p>Isi berdasarkan transaksi sebenarnya. Data disimpan di server EduPad dan langsung terbaca AI di perangkat.</p></div></div>
          <form onSubmit={submit}>
            <div className="finance-kind" role="group" aria-label="Jenis transaksi">
              <button type="button" className={kind === "expense" ? "active expense" : ""} onClick={() => changeKind("expense")}>Pengeluaran</button>
              <button type="button" className={kind === "income" ? "active income" : ""} onClick={() => changeKind("income")}>Pemasukan</button>
            </div>
            <label><span>Nominal</span><div className="money-input"><b>Rp</b><input inputMode="numeric" placeholder="0" value={amount} onChange={(event) => setAmount(event.target.value)} autoFocus /></div></label>
            <label><span>Kategori</span><select value={category} onChange={(event) => setCategory(event.target.value)}>{(kind === "expense" ? EXPENSE_CATEGORIES : INCOME_CATEGORIES).map((item) => <option key={item}>{item}</option>)}</select></label>
            <label><span>Tanggal</span><input type="date" value={date} onChange={(event) => setDate(event.target.value)} /></label>
            <label className="finance-note"><span>Catatan <small>(opsional)</small></span><input placeholder="Contoh: makan siang di kampus" value={note} onChange={(event) => setNote(event.target.value)} maxLength={100} /></label>
            <div className="finance-form-actions">{error && <span className="finance-error">{error}</span>}<button type="button" className="btn" onClick={() => setComposer(false)}>Batal</button><button className="btn btn-dark" type="submit" disabled={busy}>{busy ? "Menyimpan…" : "Simpan transaksi"}</button></div>
          </form>
        </section>
      )}

      <section className="finance-metrics">
        <Metric label="Pemasukan" value={money.format(income)} hint={formatMonth(month)} tone="positive" />
        <Metric label="Pengeluaran" value={money.format(expense)} hint={`${monthRows.filter((row) => row.kind === "expense").length} transaksi`} tone="negative" />
        <Metric label="Selisih" value={money.format(balance)} hint={balance >= 0 ? "Pemasukan masih mencukupi" : "Pengeluaran melebihi pemasukan"} tone={balance >= 0 ? "positive" : "negative"} />
        <Metric label="Sisa anggaran" value={budgetTotal ? money.format(remainingBudget) : "Belum diatur"} hint={budgetTotal ? `dari ${money.format(budgetTotal)}` : "Atur batas pada tab Anggaran"} tone={remainingBudget < 0 ? "negative" : ""} />
      </section>

      {tab === "summary" && (
        <div className="finance-grid">
          <section className="card finance-panel">
            <div className="finance-section-head"><div><h2>Penggunaan per kategori</h2></div><button className="text-button" onClick={() => setTab("budgets")}>Atur anggaran</button></div>
            {spendingByCategory.length ? <div className="finance-bars">{spendingByCategory.map((row) => <div className="finance-bar-row" key={row.name}><div><strong>{row.name}</strong><span>{money.format(row.amount)}{row.budget ? ` / ${money.format(row.budget)}` : ""}</span></div><div className="finance-bar-track"><i style={{ width: `${Math.min(100, (row.amount / maxCategory) * 100)}%` }} /><b style={{ left: `${Math.min(100, (row.budget / maxCategory) * 100)}%` }} /></div></div>)}</div> : <div className="finance-empty"><Icon name="wallet" size={28} /><strong>Belum ada pengeluaran</strong><span>Catat transaksi pertama untuk melihat pembagian kategori.</span></div>}
          </section>
          <section className="card finance-panel">
            <div className="finance-section-head"><div><h2>Transaksi terakhir</h2></div><button className="text-button" onClick={() => setTab("transactions")}>Lihat semua</button></div>
            <TransactionList rows={monthRows.slice(0, 6)} onDelete={removeTransaction} />
          </section>
        </div>
      )}

      {tab === "transactions" && <section className="card finance-panel"><div className="finance-section-head"><div><h2>Daftar transaksi</h2><p>{formatMonth(month)}</p></div></div><TransactionList rows={monthRows} onDelete={removeTransaction} /></section>}

      {tab === "budgets" && (
        <section className="card finance-panel">
          <div className="finance-section-head"><div><h2>Tetapkan batas pengeluaran</h2><p>Tersimpan saat kolom ditinggalkan; bisa juga diatur lewat suara. AI memakai angka ini untuk menjawab sisa anggaran.</p></div><strong className="finance-budget-total">{money.format(budgetTotal)}</strong></div>
          <div className="budget-grid">{EXPENSE_CATEGORIES.map((name) => <label key={name}><span>{name}</span><div className="money-input"><b>Rp</b><input inputMode="numeric" disabled={!available} value={budgets[name] || ""} placeholder="0" onBlur={() => saveBudget(name)} onChange={(event) => setBudgets((current) => ({ ...current, [name]: Math.max(0, Number(event.target.value.replace(/[^0-9]/g, "")) || 0) }))} /></div></label>)}</div>
          <div className="finance-callout"><Icon name="help" /><span>Mulailah dari kebutuhan utama seperti makan, transportasi, tempat tinggal, dan biaya kuliah. Anggaran bukan target untuk dihabiskan.</span></div>
        </section>
      )}

      {tab === "reports" && (
        <section className="card finance-panel finance-report">
          <div className="finance-section-head"><div><h2>{formatMonth(month)}</h2><p>Laporan dihitung dari transaksi yang Anda catat, tanpa perkiraan AI.</p></div><button className="btn" disabled={!monthRows.length} onClick={() => downloadCsv(monthRows, month)}><Icon name="external" size={14} />Unduh CSV</button></div>
          <div className="report-summary"><div><span>Total pemasukan</span><strong>{money.format(income)}</strong></div><div><span>Total pengeluaran</span><strong>{money.format(expense)}</strong></div><div><span>Selisih akhir</span><strong className={balance < 0 ? "bad-text" : "good-text"}>{money.format(balance)}</strong></div><div><span>Rasio tersisa</span><strong>{income ? `${savingsRate.toFixed(1)}%` : "—"}</strong></div></div>
          {monthRows.length ? <div className="report-table"><div className="report-row report-head"><span>Kategori</span><span>Terpakai</span><span>Anggaran</span><span>Status</span></div>{spendingByCategory.map((row) => { const ratio = row.budget ? row.amount / row.budget : 0; return <div className="report-row" key={row.name}><strong>{row.name}</strong><span>{money.format(row.amount)}</span><span>{row.budget ? money.format(row.budget) : "Belum diatur"}</span><span className={ratio > 1 ? "bad-text" : ratio > 0.8 ? "warn-text" : "good-text"}>{!row.budget ? "—" : ratio > 1 ? "Melebihi" : ratio > 0.8 ? "Mendekati" : "Aman"}</span></div>})}</div> : <div className="finance-empty"><Icon name="clipboard" size={28} /><strong>Laporan belum tersedia</strong><span>Tambahkan transaksi pada periode ini agar laporan dapat dihitung.</span></div>}
          <div className="finance-report-note">Ringkasan: pemasukan {compactMoney.format(income)}, pengeluaran {compactMoney.format(expense)}, dan selisih {compactMoney.format(balance)}.</div>
        </section>
      )}
    </div>
  );
}

function TransactionList({ rows, onDelete }: { rows: FinanceTransaction[]; onDelete: (row: FinanceTransaction) => void }) {
  if (!rows.length) return <div className="finance-empty"><Icon name="clipboard" size={28} /><strong>Belum ada transaksi</strong><span>Data hanya muncul setelah Anda mencatat transaksi sebenarnya.</span></div>;
  return <div className="transaction-list">{rows.map((row) => <article key={row.id}><span className={`transaction-icon ${row.kind}`} aria-hidden>{row.kind === "income" ? "+" : "−"}</span><div><strong>{row.note || row.category}{row.source === "suara" && <span className="pill chip voice-chip" title="Dicatat AI EduPad dari ucapan di perangkat">Suara</span>}</strong><span>{row.category} · {dateLabel.format(new Date(`${row.date}T12:00:00`))}</span></div><b className={row.kind}>{row.kind === "income" ? "+" : "−"}{money.format(row.amount)}</b><button type="button" onClick={() => onDelete(row)} aria-label={`Hapus ${row.note || row.category}`} title="Hapus transaksi">×</button></article>)}</div>;
}
