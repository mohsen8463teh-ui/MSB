from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..analysis.strategy_baseline import generate_sma_trend_signals
from ..data.validation import validate_ohlcv
from .engine import run_long_only_backtest


def evaluate_baseline_holdout(
    candles: Sequence[Mapping[str, Any]],
    *,
    split_index: int,
    initial_cash: float = 100_000.0,
    fee_bps: float = 10.0,
    slippage_bps: float = 5.0,
    max_exposure_fraction: float = 0.95,
) -> dict[str, Any]:
    """Evaluate the fixed baseline on a chronological holdout segment.

    The pre-split candles provide indicator warmup only. No parameters are fit.
    The test starts flat; if the baseline condition is already true at the
    first test close, an entry is scheduled for the following open.
    """
    if not candles:
        raise ValueError("candles must not be empty")
    if isinstance(split_index, bool) or not isinstance(split_index, int):
        raise ValueError("split_index must be an integer")
    if split_index < 200 or split_index >= len(candles) - 1:
        raise ValueError("split_index must leave at least 200 warmup and 2 test bars")

    last_timestamp = float(candles[-1]["timestamp"])
    checked = validate_ohlcv(candles, now=last_timestamp + 1)
    if not checked["valid"] or not checked["complete"]:
        raise ValueError("invalid or incomplete candles: " + ", ".join(checked["issues"]))
    series = checked["candles"]

    signals = generate_sma_trend_signals(series)
    test_candles = series[split_index:]
    entries = signals["entry_signals"][split_index:]
    exits = signals["exit_signals"][split_index:]
    if signals["bullish_condition"][split_index]:
        entries[0] = True

    result = run_long_only_backtest(
        test_candles,
        entries,
        exits,
        initial_cash=initial_cash,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
        max_exposure_fraction=max_exposure_fraction,
    )
    return {
        "method": "fixed_chronological_holdout",
        "strategy_id": signals["strategy_id"],
        "research_only": True,
        "training_period_used_for_parameter_fitting": False,
        "train_bars": split_index,
        "test_bars": len(test_candles),
        "train_end_timestamp": series[split_index - 1]["timestamp"],
        "test_start_timestamp": test_candles[0]["timestamp"],
        "test_end_timestamp": test_candles[-1]["timestamp"],
        "results": result,
    }
