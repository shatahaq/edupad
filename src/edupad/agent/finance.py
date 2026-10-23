"""Keuangan mahasiswa: satu sumber data untuk dashboard (input manual) dan perangkat (suara).

Transaksi & anggaran disimpan di Supabase (`finance_transactions`, `finance_budgets`,
lihat supabase/migrations/20261017_finance_tutor.sql). AI agent mencatat lewat tool
`record_transaction` saat mahasiswa bicara, misalnya "tadi beli makan dua puluh lima ribu";
transaksi dari perangkat diberi source "suara" agar terlihat di dashboard.
"""

from __future__ import annotations

import logging
from calendar import monthrange
from collections import defaultdict
from datetime import date, datetime, timedelta

from edupad.config import WIB, get_settings
from edupad.core.supabase import SupabaseClient, SupabaseError

log = logging.getLogger(__name__)

TRANSACTIONS = "finance_transactions"
BUDGETS = "finance_budgets"
# Sama dengan pilihan di dashboard (dashboard/src/lib/finance.ts).
EXPENSE_CATEGORIES = [
    "Makan",
    "Transportasi",
    "Tempat tinggal",
    "Kuliah",
    "Internet",
    "Kesehatan",
    "Hiburan",
    "Lainnya",
]
INCOME_CATEGORIES = ["Kiriman keluarga", "Beasiswa", "Kerja sampingan", "Pengembalian", "Lainnya"]
KINDS = {"pengeluaran": "expense", "pemasukan": "income", "expense": "expense", "income": "income"}
SOURCES = frozenset({"suara", "dashboard", "impor"})
MAX_AMOUNT = 1_000_000_000
MAX_NOTE = 200
MAX_ROWS = 5_000
PERIODS = ("hari_ini", "minggu_ini", "bulan_ini", "bulan_lalu", "30_hari")
BUDGET_WARNING = 0.9  # pengeluaran >= 90% anggaran kategori bulan ini -> peringatan
UNDO_WINDOW = timedelta(hours=12)  # "hapus yang tadi" hanya untuk catatan suara terbaru
# Riwayat percakapan yang dikirim ke LLM hanya memuat jawaban, bukan tool yang sudah dijalankan
# (agent/memory.py turn_messages), jadi agent kadang "menyusul" mencatat lagi transaksi dari
# giliran sebelumnya. Catatan suara yang sama persis dalam rentang ini karena itu dianggap
# pengulangan; transaksi yang memang terjadi dua kali dicatat dengan repeat=True.
DUPLICATE_WINDOW = timedelta(minutes=10)
DUPLICATE_SCAN = 20  # catatan suara terakhir yang diperiksa
FIELDS = "id,kind,amount,category,note,occurred_on,source,created_at"


class FinanceUnavailable(RuntimeError):
    """Tabel keuangan belum dibuat atau Supabase tidak bisa dipakai."""


class FinanceInputError(ValueError):
    pass


class FinanceDuplicate(FinanceInputError):
    """Transaksi suara yang sama persis baru saja dicatat; `existing` = baris yang sudah ada."""

    def __init__(self, existing: dict):
        super().__init__("transaksi yang sama baru saja dicatat lewat suara")
        self.existing = existing


def rupiah(amount: float) -> str:
    return "Rp" + f"{round(amount):,}".replace(",", ".")


def _today() -> date:
    return datetime.now(WIB).date()


def _created(row: dict) -> datetime:
    stamp = datetime.fromisoformat(str(row["created_at"]).replace("Z", "+00:00"))
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=WIB)


def _category(kind: str, category: str | None) -> str:
    options = EXPENSE_CATEGORIES if kind == "expense" else INCOME_CATEGORIES
    wanted = (category or "").strip().lower()
    for option in options:
        if option.lower() == wanted:
            return option
    for option in options:  # "makan siang" -> Makan, "kiriman" -> Kiriman keluarga
        if wanted and (wanted in option.lower() or option.lower() in wanted):
            return option
    return "Lainnya"


def period_range(period: str, today: date | None = None) -> tuple[date, date]:
    """Rentang tanggal (inklusif) untuk periode ringkasan."""
    today = today or _today()
    if period == "hari_ini":
        return today, today
    if period == "minggu_ini":
        return today - timedelta(days=today.weekday()), today
    if period == "bulan_lalu":
        last = today.replace(day=1) - timedelta(days=1)
        return last.replace(day=1), last
    if period == "30_hari":
        return today - timedelta(days=29), today
    return today.replace(day=1), today.replace(day=monthrange(today.year, today.month)[1])


class FinanceStore:
    def __init__(self, user_id: str | None = None, db: SupabaseClient | None = None):
        self.user_id = user_id or get_settings().user_id
        try:
            self.db = db or SupabaseClient()
        except SupabaseError as e:
            raise FinanceUnavailable(str(e)) from e

    def _run(self, fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except SupabaseError as e:
            text = str(e)
            if "PGRST205" in text or "42P01" in text or "does not exist" in text:
                raise FinanceUnavailable(
                    "tabel keuangan belum dibuat (supabase/migrations/20261017_finance_tutor.sql)"
                ) from e
            raise FinanceUnavailable(f"Supabase: {text}") from e

    # ------------------------------ transaksi ------------------------------
    def add(
        self,
        kind: str,
        amount: float,
        category: str | None,
        note: str = "",
        occurred_on: str | date | None = None,
        source: str = "dashboard",
        repeat: bool = False,
    ) -> dict:
        """Simpan satu transaksi. `repeat`: catat walau kembar dengan catatan suara barusan."""
        kind = KINDS.get((kind or "").strip().lower(), "")
        if not kind:
            raise FinanceInputError("jenis harus pemasukan atau pengeluaran")
        try:
            value = round(float(amount))
        except (TypeError, ValueError):
            raise FinanceInputError("nominal harus angka rupiah") from None
        if not 0 < value <= MAX_AMOUNT:
            raise FinanceInputError("nominal harus lebih dari 0 dan masuk akal")
        if isinstance(occurred_on, str) and occurred_on.strip():
            try:
                day = date.fromisoformat(occurred_on.strip()[:10])
            except ValueError:
                raise FinanceInputError("tanggal harus YYYY-MM-DD") from None
        elif isinstance(occurred_on, date):
            day = occurred_on
        else:
            day = _today()
        if day > _today() + timedelta(days=1):
            raise FinanceInputError("tanggal transaksi tidak boleh di masa depan")
        row = {
            "user_id": self.user_id,
            "kind": kind,
            "amount": value,
            "category": _category(kind, category),
            "note": " ".join(str(note or "").split())[:MAX_NOTE],
            "occurred_on": day.isoformat(),
            "source": source if source in SOURCES else "dashboard",
        }
        if row["source"] == "suara" and not repeat:
            existing = self.duplicate(row)
            if existing:
                raise FinanceDuplicate(existing)
        return self._run(self.db.insert, TRANSACTIONS, [row])[0]

    def duplicate(self, row: dict) -> dict | None:
        """Catatan suara yang sama persis (jenis, nominal, kategori, tanggal) dan masih baru."""
        oldest = datetime.now(WIB) - DUPLICATE_WINDOW
        keys = ("kind", "amount", "category", "occurred_on")
        for other in self.recent_voice(DUPLICATE_SCAN):
            if _created(other) < oldest:
                break  # diurutkan dari yang terbaru
            if all(str(other[k]) == str(row[k]) for k in keys):
                return other
        return None

    def transactions(self, start: date | None = None, end: date | None = None) -> list[dict]:
        rows = self._run(
            self.db.select,
            TRANSACTIONS,
            FIELDS,
            user_id=f"eq.{self.user_id}",
            order="occurred_on.desc,created_at.desc",
            limit=str(MAX_ROWS),
        )
        return [
            r
            for r in rows
            if (start is None or str(r["occurred_on"]) >= start.isoformat())
            and (end is None or str(r["occurred_on"]) <= end.isoformat())
        ]

    def delete(self, transaction_id: str) -> None:
        self._run(
            self.db.delete, TRANSACTIONS, id=f"eq.{transaction_id}", user_id=f"eq.{self.user_id}"
        )

    def recent_voice(self, limit: int = 1) -> list[dict]:
        """Catatan suara terbaru lebih dulu."""
        return self._run(
            self.db.select,
            TRANSACTIONS,
            FIELDS,
            user_id=f"eq.{self.user_id}",
            source="eq.suara",
            order="created_at.desc",
            limit=str(limit),
        )

    def last_voice(self) -> dict | None:
        rows = self.recent_voice()
        return rows[0] if rows else None

    # ------------------------------ anggaran -------------------------------
    def budgets(self) -> dict[str, int]:
        rows = self._run(self.db.select, BUDGETS, "category,amount", user_id=f"eq.{self.user_id}")
        return {r["category"]: int(r["amount"]) for r in rows}

    def set_budget(self, category: str, amount: float) -> dict:
        name = _category("expense", category)
        try:
            value = max(0, round(float(amount)))
        except (TypeError, ValueError):
            raise FinanceInputError("nominal anggaran harus angka rupiah") from None
        if value > MAX_AMOUNT:
            raise FinanceInputError("nominal anggaran tidak masuk akal")
        row = {
            "user_id": self.user_id,
            "category": name,
            "amount": value,
            "updated_at": datetime.now(WIB).isoformat(),
        }
        self._run(self.db.upsert, BUDGETS, [row], on_conflict="user_id,category")
        return row

    # ------------------------------ ringkasan ------------------------------
    def summary(self, period: str = "bulan_ini", category: str | None = None) -> dict:
        start, end = period_range(period if period in PERIODS else "bulan_ini")
        rows = self.transactions(start, end)
        wanted = _category("expense", category) if category else None
        if wanted:
            rows = [r for r in rows if r["category"] == wanted]
        spent: dict[str, int] = defaultdict(int)
        income = expense = 0
        for r in rows:
            if r["kind"] == "income":
                income += int(r["amount"])
            else:
                expense += int(r["amount"])
                spent[r["category"]] += int(r["amount"])
        return {
            "periode": period,
            "dari": start.isoformat(),
            "sampai": end.isoformat(),
            "pemasukan": income,
            "pengeluaran": expense,
            "saldo": income - expense,
            "per_kategori": dict(sorted(spent.items(), key=lambda kv: -kv[1])),
            "jumlah_transaksi": len(rows),
            "kategori": wanted,
        }

    def budget_status(self, today: date | None = None) -> list[dict]:
        """Pemakaian anggaran bulan berjalan per kategori yang punya anggaran."""
        budgets = self.budgets()
        if not budgets:
            return []
        start, end = period_range("bulan_ini", today)
        spent: dict[str, int] = defaultdict(int)
        for r in self.transactions(start, end):
            if r["kind"] == "expense":
                spent[r["category"]] += int(r["amount"])
        return [
            {
                "kategori": name,
                "anggaran": limit,
                "terpakai": spent[name],
                "sisa": limit - spent[name],
                "persen": round(spent[name] * 100 / limit) if limit else None,
            }
            for name, limit in budgets.items()
            if limit > 0
        ]


# --------------------------------- tools ----------------------------------
def _store() -> FinanceStore:
    return FinanceStore()


def _budget_line(store: FinanceStore, category: str) -> dict | None:
    status = next((b for b in store.budget_status() if b["kategori"] == category), None)
    if not status:
        return None
    return {
        "anggaran_bulan_ini": status["anggaran"],
        "terpakai": status["terpakai"],
        "sisa": status["sisa"],
        "persen_terpakai": status["persen"],
    }


def record_transaction(
    kind: str,
    amount: float,
    category: str | None = None,
    note: str = "",
    date: str | None = None,
    repeat: bool = False,
) -> dict:
    """Catat satu transaksi dari ucapan mahasiswa (source "suara")."""
    try:
        store = _store()
        row = store.add(kind, amount, category, note, date, source="suara", repeat=repeat)
        jenis = "pengeluaran" if row["kind"] == "expense" else "pemasukan"
        result = {
            "tercatat": True,
            "jenis": jenis,
            "nominal": int(row["amount"]),
            "nominal_teks": rupiah(row["amount"]),
            "kategori": row["category"],
            "tanggal": row["occurred_on"],
            "catatan": row["note"],
            # Masuk ke riwayat percakapan (assistant.ask -> memory.turn_messages).
            "aksi": f"catat {jenis} {row['category']} {rupiah(row['amount'])} "
            f"({row['occurred_on']})",
        }
        if row["kind"] == "expense":
            budget = _budget_line(store, row["category"])
            if budget:
                result["anggaran"] = budget
        return result
    except FinanceDuplicate as e:
        row = e.existing
        return {
            "tercatat": False,
            "sudah_dicatat": True,
            "nominal_teks": rupiah(row["amount"]),
            "kategori": row["category"],
            "tanggal": row["occurred_on"],
            "petunjuk": "transaksi ini sudah ada, jadi tidak dicatat dua kali. Bila mahasiswa "
            "TIDAK menyebutnya di pertanyaan terakhir, ini pengulangan dari giliran sebelumnya: "
            "abaikan saja, jangan disebut sama sekali, jawab hanya soal yang baru disebut. Bila "
            "mahasiswa memang baru menyebutnya, tanyakan apakah ini pembelian kedua; kalau iya, "
            "panggil lagi dengan repeat=true.",
        }
    except (FinanceUnavailable, FinanceInputError) as e:
        return {"error": str(e)}


def finance_summary(period: str = "bulan_ini", category: str | None = None) -> dict:
    try:
        store = _store()
        result = store.summary(period, category)
        result["anggaran"] = store.budget_status()
        return result
    except FinanceUnavailable as e:
        return {"error": str(e)}


def undo_last_transaction() -> dict:
    """Hapus catatan suara terakhir (koreksi "eh salah, hapus yang tadi")."""
    try:
        store = _store()
        last = store.last_voice()
        if not last:
            return {"error": "belum ada transaksi yang dicatat lewat suara"}
        created = datetime.fromisoformat(str(last["created_at"]).replace("Z", "+00:00"))
        if datetime.now(WIB) - created > UNDO_WINDOW:
            return {
                "error": "catatan suara terakhir sudah lebih dari 12 jam; hapus dari dashboard",
                "terakhir": {"nominal_teks": rupiah(last["amount"]), "kategori": last["category"]},
            }
        store.delete(last["id"])
        jenis = "pengeluaran" if last["kind"] == "expense" else "pemasukan"
        return {
            "dihapus": True,
            "jenis": jenis,
            "nominal_teks": rupiah(last["amount"]),
            "kategori": last["category"],
            "tanggal": last["occurred_on"],
            "aksi": f"hapus catatan {jenis} {last['category']} {rupiah(last['amount'])}",
        }
    except FinanceUnavailable as e:
        return {"error": str(e)}


def set_budget(category: str, amount: float) -> dict:
    try:
        store = _store()
        row = store.set_budget(category, amount)
        return {
            "anggaran_diatur": True,
            "kategori": row["category"],
            "nominal_teks": rupiah(row["amount"]),
            "aksi": f"atur anggaran {row['category']} {rupiah(row['amount'])} per bulan",
            **(_budget_line(store, row["category"]) or {}),
        }
    except (FinanceUnavailable, FinanceInputError) as e:
        return {"error": str(e)}


TOOLS = {
    "record_transaction": record_transaction,
    "finance_summary": finance_summary,
    "undo_last_transaction": undo_last_transaction,
    "set_budget": set_budget,
}

SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "record_transaction",
            "description": "Catat pemasukan/pengeluaran yang diucapkan mahasiswa (mis. 'tadi beli "
            "makan 25 ribu', 'dapat kiriman sejuta'). Langsung catat bila jenis & nominal jelas. "
            "Hanya untuk transaksi yang BARU disebut sekarang; yang sudah dicatat di giliran "
            "sebelumnya jangan dicatat lagi.",
            "parameters": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": ["pengeluaran", "pemasukan"]},
                    "amount": {
                        "type": "integer",
                        "description": "nominal rupiah, mis. 'dua puluh lima ribu' = 25000",
                    },
                    "category": {
                        "type": "string",
                        "enum": sorted(set(EXPENSE_CATEGORIES + INCOME_CATEGORIES)),
                    },
                    "note": {
                        "type": "string",
                        "description": "keterangan singkat, mis. 'nasi goreng'",
                    },
                    "date": {"type": "string", "description": "YYYY-MM-DD, default hari ini"},
                    "repeat": {
                        "type": "boolean",
                        "description": "true hanya bila mahasiswa menegaskan transaksi yang "
                        "sama persis memang terjadi lagi; selain itu jangan diisi",
                    },
                },
                "required": ["kind", "amount", "category"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finance_summary",
            "description": "Ringkasan keuangan: total pemasukan/pengeluaran, per kategori, dan sisa "
            "anggaran bulan ini.",
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {"type": "string", "enum": list(PERIODS)},
                    "category": {"type": "string", "description": "satu kategori (opsional)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "undo_last_transaction",
            "description": "Hapus transaksi terakhir yang dicatat lewat suara (koreksi salah catat).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_budget",
            "description": "Atur anggaran bulanan satu kategori pengeluaran, mis. 'anggaran makan "
            "lima ratus ribu'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": EXPENSE_CATEGORIES},
                    "amount": {"type": "integer", "description": "nominal rupiah per bulan"},
                },
                "required": ["category", "amount"],
            },
        },
    },
]
