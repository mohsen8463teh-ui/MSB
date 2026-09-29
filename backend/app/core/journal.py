"""Append-only research journal primitives.

Records are observations, not orders. TEST/FIXTURE data must never be treated as
live evidence; callers must explicitly label the source and keep NO_TRADE.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

ALLOWED_MARKETS = {"iran_equity", "crypto_spot"}
ALLOWED_DIRECTIONS = {"LONG", "FLAT"}
ALLOWED_SOURCES = {"LIVE_PROVIDER", "HISTORICAL", "TEST", "FIXTURE"}


def create_journal_record(
    *, market: str, symbol: str, horizon: str, direction: str,
    decision: str = "NO_TRADE", source_type: str,
    evidence: list[str] | None = None, data_as_of: str | None = None,
    entry: float | None = None, stop: float | None = None,
    targets: list[float] | None = None, protocol_version: str = "unknown",
    model_version: str = "none", notes: str = "",
) -> dict[str, Any]:
    """Build a validated immutable-style journal event; never place an order."""
    if market not in ALLOWED_MARKETS:
        raise ValueError("unsupported market")
    if not isinstance(symbol, str) or not symbol.strip() or len(symbol.strip()) > 32:
        raise ValueError("invalid symbol")
    if direction not in ALLOWED_DIRECTIONS:
        raise ValueError("direction must be LONG or FLAT")
    if decision != "NO_TRADE":
        raise ValueError("journal cannot authorize a trade")
    if source_type not in ALLOWED_SOURCES:
        raise ValueError("invalid source_type")
    if source_type in {"TEST", "FIXTURE"} and data_as_of is not None:
        raise ValueError("test/fixture records cannot claim a live as_of timestamp")
    for name, value in (("entry", entry), ("stop", stop)):
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0):
            raise ValueError(f"{name} must be positive numeric or null")
    if targets is not None and any(
        isinstance(x, bool) or not isinstance(x, (int, float)) or x <= 0 for x in targets
    ):
        raise ValueError("targets must contain positive numbers")
    if entry is not None and stop is not None and direction == "LONG" and stop >= entry:
        raise ValueError("long stop must be below entry")
    if evidence is not None and (not isinstance(evidence, list) or any(not isinstance(x, str) for x in evidence)):
        raise ValueError("evidence must be a list of strings")
    if not isinstance(notes, str) or len(notes) > 4000:
        raise ValueError("notes must be text up to 4000 characters")
    return {
        "journal_id": str(uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "market": market, "symbol": symbol.strip().upper(), "horizon": horizon,
        "direction": direction, "decision": "NO_TRADE", "source_type": source_type,
        "data_as_of": data_as_of, "entry": entry, "stop": stop,
        "targets": list(targets or []), "evidence": list(evidence or []),
        "protocol_version": protocol_version, "model_version": model_version,
        "outcome": None, "notes": notes,
    }
