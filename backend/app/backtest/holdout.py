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

    checked = validate_ohlcv(candles)
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
    closed_trades = result["closed_trades"]
    sample_status = "INSUFFICIENT_TRADES" if closed_trades < 30 else "TRADE_COUNT_OK_REQUIRES_FURTHER_VALIDATION"
    return {
        "method": "fixed_chronological_holdout",
        "sample_status": sample_status,
        "minimum_closed_trades_for_screening": 30,
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


def evaluate_baseline_walk_forward(
    candles: Sequence[Mapping[str, Any]],
    *,
    initial_train_bars: int = 400,
    test_bars: int = 90,
    step_bars: int | None = None,
    initial_cash: float = 100_000.0,
    fee_bps: float = 10.0,
    slippage_bps: float = 5.0,
    max_exposure_fraction: float = 0.95,
) -> dict[str, Any]:
    """Run non-overlapping chronological test windows using a fixed baseline.

    Each fold is independently flat at its start. Earlier data is used only
    for causal indicator warmup; no parameters are fitted or selected.
    """
    if isinstance(initial_train_bars, bool) or not isinstance(initial_train_bars, int) or initial_train_bars < 200:
        raise ValueError("initial_train_bars must be an integer >= 200")
    if isinstance(test_bars, bool) or not isinstance(test_bars, int) or test_bars < 2:
        raise ValueError("test_bars must be an integer >= 2")
    if step_bars is None:
        step_bars = test_bars
    if isinstance(step_bars, bool) or not isinstance(step_bars, int) or step_bars < test_bars:
        raise ValueError("step_bars must be an integer >= test_bars to prevent overlap")
    if len(candles) < initial_train_bars + test_bars:
        raise ValueError("not enough candles for one complete walk-forward fold")

    checked = validate_ohlcv(candles)
    if not checked["valid"] or not checked["complete"]:
        raise ValueError("invalid or incomplete candles: " + ", ".join(checked["issues"]))
    candles = checked["candles"]

    folds: list[dict[str, Any]] = []
    start = initial_train_bars
    while start + 1 < len(candles):
        end = min(start + test_bars, len(candles))
        if end - start < 2:
            break
        fold = evaluate_baseline_holdout(
            candles[:end],
            split_index=start,
            initial_cash=initial_cash,
            fee_bps=fee_bps,
            slippage_bps=slippage_bps,
            max_exposure_fraction=max_exposure_fraction,
        )
        folds.append({
            "fold": len(folds) + 1,
            "train_end_timestamp": fold["train_end_timestamp"],
            "test_start_timestamp": fold["test_start_timestamp"],
            "test_end_timestamp": fold["test_end_timestamp"],
            "train_bars": fold["train_bars"],
            "test_bars": fold["test_bars"],
            "sample_status": fold["sample_status"],
            "results": fold["results"],
        })
        start += step_bars

    closed_trades = sum(item["results"]["closed_trades"] for item in folds)
    return {
        "method": "expanding_window_walk_forward",
        "strategy_id": "sma_trend_baseline_v1",
        "research_only": True,
        "parameters_fitted": False,
        "overlapping_test_windows": False,
        "fold_count": len(folds),
        "total_test_bars": sum(item["test_bars"] for item in folds),
        "closed_trades": closed_trades,
        "sample_status": "INSUFFICIENT_TRADES" if closed_trades < 30 else "TRADE_COUNT_OK_REQUIRES_FURTHER_VALIDATION",
        "minimum_closed_trades_for_screening": 30,
        "folds": folds,
    }
