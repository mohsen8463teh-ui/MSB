from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any


_REQUIRED_FIELDS = ("timestamp", "open", "high", "low", "close", "volume")


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def validate_ohlcv(
    candles: Sequence[Mapping[str, Any]] | None,
    *,
    interval_seconds: int | None = None,
    now: float | None = None,
) -> dict[str, Any]:
    """Validate chronological OHLCV candles without silently repairing prices.

    Timestamps are Unix seconds. Completeness gaps are checked only when the
    caller supplies an expected interval (useful for fixed-interval crypto data).
    """
    issues: list[str] = []
    normalized: list[dict[str, float]] = []

    if not candles:
        return {
            "valid": False,
            "complete": False,
            "candles": [],
            "issues": ["no_candles"],
        }

    if interval_seconds is not None and (
        isinstance(interval_seconds, bool)
        or not isinstance(interval_seconds, int)
        or interval_seconds <= 0
    ):
        raise ValueError("interval_seconds must be a positive integer")

    if now is None:
        current_time = datetime.now(timezone.utc).timestamp()
    else:
        current_time = _finite_number(now)
        if current_time is None:
            raise ValueError("now must be a finite numeric timestamp")

    previous_timestamp: float | None = None

    for index, candle in enumerate(candles):
        if not isinstance(candle, Mapping):
            issues.append(f"candle_{index}_not_an_object")
            continue

        missing = [field for field in _REQUIRED_FIELDS if field not in candle]
        if missing:
            issues.append(f"candle_{index}_missing_fields")
            continue

        values = {field: _finite_number(candle[field]) for field in _REQUIRED_FIELDS}
        if any(value is None for value in values.values()):
            issues.append(f"candle_{index}_contains_non_finite_or_non_numeric_values")
            continue

        timestamp = values["timestamp"]
        open_price = values["open"]
        high = values["high"]
        low = values["low"]
        close = values["close"]
        volume = values["volume"]

        if timestamp <= 0:
            issues.append(f"candle_{index}_invalid_timestamp")
            continue
        if timestamp > current_time:
            issues.append(f"candle_{index}_timestamp_in_future")
            continue
        if min(open_price, high, low, close) <= 0:
            issues.append(f"candle_{index}_non_positive_price")
            continue
        if volume < 0:
            issues.append(f"candle_{index}_negative_volume")
            continue
        if high < max(open_price, low, close) or low > min(open_price, high, close):
            issues.append(f"candle_{index}_inconsistent_ohlc")
            continue

        if previous_timestamp is not None:
            if timestamp <= previous_timestamp:
                issues.append(f"candle_{index}_timestamp_not_strictly_increasing")
                continue
            if (
                interval_seconds is not None
                and timestamp - previous_timestamp > interval_seconds * 1.5
            ):
                issues.append(f"gap_before_candle_{index}")

        normalized.append(
            {
                "timestamp": timestamp,
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
            }
        )
        previous_timestamp = timestamp

    structural_issues = [
        issue
        for issue in issues
        if not issue.startswith("gap_before_candle_")
    ]
    return {
        "valid": len(normalized) == len(candles) and not structural_issues,
        "complete": not issues,
        "candles": normalized,
        "issues": issues,
    }
