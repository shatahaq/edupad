export const FINANCE_TRANSACTIONS_KEY = "edupad-student-finance-transactions-v1";
export const FINANCE_BUDGETS_KEY = "edupad-student-finance-budgets-v1";

export type FinanceKind = "income" | "expense";

export interface FinanceTransaction {
  id: string;
  kind: FinanceKind;
  amount: number;
  category: string;
  date: string;
  note: string;
  createdAt: string;
  /** suara = dicatat AI dari perangkat EduPad. */
  source?: "suara" | "dashboard" | "impor";
}

export type FinanceBudgets = Record<string, number>;

function read<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

export function loadFinanceTransactions() {
  return read<FinanceTransaction[]>(FINANCE_TRANSACTIONS_KEY, []);
}

export function loadFinanceBudgets() {
  return read<FinanceBudgets>(FINANCE_BUDGETS_KEY, {});
}

/**
 * Data keuangan versi lama tersimpan di localStorage browser. Sekarang sumbernya Supabase
 * (Office API); fungsi baca di atas hanya dipakai untuk memindahkan data lama sekali.
 */
export function clearLegacyFinance() {
  try {
    localStorage.removeItem(FINANCE_TRANSACTIONS_KEY);
    localStorage.removeItem(FINANCE_BUDGETS_KEY);
  } catch {
    // storage diblokir: tidak ada yang perlu dihapus
  }
}
