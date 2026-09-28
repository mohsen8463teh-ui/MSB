from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..data.validation import validate_ohlcv


STRATEGY_ID = "sma_trend_baseline_v1"


def generate_sma_trend_signals(
    candles: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Generate research-only long entry/exit flags at candle close.

    Entry occurs when SMA20 > SMA50 and close > SMA200 becomes true.
    Exit occurs when that combined condition becomes false. The returned
    flags are not execution prices; the backtester fills them next candle open.
    """
    if not candles:
        raise ValueError("candles must not be empty")
    last_timestamp = float(candles[-1]["timestamp"])
    checked = validate_ohlcv(candles, now=last_timestamp + 1)
    if not checked["valid"] or not checked["complete"]:
        raise ValueError("invalid candle series: " + ", ".join(checked["issues"]))

    series = checked["candles"]
    if len(series) < 200:
        raise ValueError("at least 200 validated candles are required")
    closes = [item["close"] for item in series]
    entries = [False] * len(series)
    exits = [False] * len(series)
    bullish_conditions = [False] * len(series)
    previous_bullish = False

    for index in range(199, len(series)):
        sma20 = sum(closes[index - 19 : index + 1]) / 20
        sma50 = sum(closes[index - 49 : index + 1]) / 50
        sma200 = sum(closes[index - 199 : index + 1]) / 200
        bullish = sma20 > sma50 and closes[index] > sma200
        bullish_conditions[index] = bullish

        if bullish and not previous_bullish:
            entries[index] = True
        elif previous_bullish and not bullish:
            exits[index] = True
        previous_bullish = bullish

    return {
        "strategy_id": STRATEGY_ID,
        "entry_signals": entries,
        "exit_signals": exits,
        "bullish_condition": bullish_conditions,
        "signal_timing": "candle_close",
        "execution_timing": "next_candle_open",
        "research_only": True,
    }
