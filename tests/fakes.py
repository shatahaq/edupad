"""Tiruan bersama untuk test (tanpa jaringan)."""

from datetime import datetime

from edupad.config import WIB


class FakeDb:
    """SupabaseClient di memori: filter PostgREST `eq.`/`gt.`, `order=...desc`, `limit`."""

    def __init__(self):
        self.tables = {"agent_sessions": [], "agent_turns": [], "agent_memories": []}
        self.next_id = 1

    def _match(self, row, filters):
        for key, cond in filters.items():
            if key in ("order", "limit"):
                continue
            op, value = cond.split(".", 1)
            if (op == "eq" and str(row.get(key)) != value) or (
                op == "gt" and not row.get(key) > int(value)
            ):
                return False
        return True

    def select(self, table, columns, **filters):
        rows = [r for r in self.tables[table] if self._match(r, filters)]
        if filters.get("order", "").endswith(".desc"):
            rows = rows[::-1]
        return [dict(r) for r in rows[: int(filters.get("limit", 10**6))]]

    def insert(self, table, rows):
        out = []
        for row in rows:
            row = dict(row, id=row.get("id", self.next_id))
            if table == "agent_sessions":
                row = {
                    "id": f"s{self.next_id}",
                    "summary": None,
                    "summarized_until": 0,
                    "last_active": datetime.now(WIB).isoformat(),
                    **{k: v for k, v in row.items() if k != "id"},
                }
            self.next_id += 1
            self.tables[table].append(row)
            out.append(dict(row))
        return out

    def upsert(self, table, rows, on_conflict):
        self.insert(table, rows)

    def update(self, table, values, **filters):
        for row in self.tables[table]:
            if self._match(row, filters):
                row.update(values)

    def delete(self, table, **filters):
        self.tables[table] = [r for r in self.tables[table] if not self._match(r, filters)]
