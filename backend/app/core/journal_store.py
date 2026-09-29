"""SQLite persistence for NO_TRADE research journal events."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class JournalStore:
    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS journal (
                    journal_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    market TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    horizon TEXT NOT NULL,
                    decision TEXT NOT NULL CHECK(decision = 'NO_TRADE'),
                    source_type TEXT NOT NULL,
                    record_json TEXT NOT NULL
                )
            """)
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_journal_created ON journal(created_at DESC)"
            )

    def _connect(self):
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def append(self, record: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(record, dict) or record.get("decision") != "NO_TRADE":
            raise ValueError("only validated NO_TRADE records can be stored")
        required = ("journal_id", "created_at", "market", "symbol", "horizon", "source_type")
        if any(not record.get(key) for key in required):
            raise ValueError("record is missing required fields")
        payload = json.dumps(record, ensure_ascii=False, allow_nan=False)
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO journal
                (journal_id, created_at, market, symbol, horizon, decision, source_type, record_json)
                VALUES (?, ?, ?, ?, ?, 'NO_TRADE', ?, ?)""",
                (record["journal_id"], record["created_at"], record["market"],
                 record["symbol"], record["horizon"], record["source_type"], payload),
            )
        return dict(record)

    def list_records(self, *, limit: int = 100, offset: int = 0,
                     market: str | None = None, symbol: str | None = None) -> list[dict[str, Any]]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            raise ValueError("offset must be non-negative")
        clauses, params = [], []
        if market:
            clauses.append("market = ?")
            params.append(market)
        if symbol:
            clauses.append("symbol = ?")
            params.append(symbol.strip().upper())
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT record_json FROM journal" + where +
                " ORDER BY created_at DESC, journal_id DESC LIMIT ? OFFSET ?",
                (*params, limit, offset),
            ).fetchall()
        return [json.loads(row["record_json"]) for row in rows]

    def get(self, journal_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT record_json FROM journal WHERE journal_id = ?", (journal_id,)
            ).fetchone()
        return json.loads(row["record_json"]) if row else None
