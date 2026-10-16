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

export function saveFinanceTransactions(transactions: FinanceTransaction[]) {
  localStorage.setItem(FINANCE_TRANSACTIONS_KEY, JSON.stringify(transactions));
}

export function saveFinanceBudgets(budgets: FinanceBudgets) {
  localStorage.setItem(FINANCE_BUDGETS_KEY, JSON.stringify(budgets));
}
