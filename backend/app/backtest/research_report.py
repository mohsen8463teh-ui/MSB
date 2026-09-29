from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..analysis.strategy_baseline import generate_sma_trend_signals
from .engine import run_long_only_backtest
from .holdout import evaluate_baseline_walk_forward
from .monte_carlo import bootstrap_trade_returns


def evaluate_research_universe(
    datasets: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    initial_train_bars: int = 400,
    test_bars: int = 90,
    step_bars: int | None = None,
    initial_cash: float = 100_000.0,
    fee_bps: float = 10.0,
    slippage_bps: float = 5.0,
    max_exposure_fraction: float = 0.95,
    simulations: int = 2_000,
    seed: int = 7,
    minimum_trades: int = 30,
) -> dict[str, Any]:
    """Evaluate each asset/timeframe independently; never pool their trades."""
    if not isinstance(datasets, Mapping) or not datasets:
        raise ValueError("datasets must be a non-empty mapping")
    # Validate the complete report configuration at its public boundary so
    # callers get deterministic errors before any dataset is processed.
    integer_parameters = {
        "initial_train_bars": (initial_train_bars, 200),
        "test_bars": (test_bars, 2),
        "simulations": (simulations, 100),
        "minimum_trades": (minimum_trades, 1),
    }
    for name, (value, minimum) in integer_parameters.items():
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            raise ValueError(f"{name} must be an integer >= {minimum}")
    if step_bars is not None and (
        isinstance(step_bars, bool) or not isinstance(step_bars, int) or step_bars < test_bars
    ):
        raise ValueError("step_bars must be an integer >= test_bars")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    numeric_parameters = {
        "initial_cash": initial_cash,
        "fee_bps": fee_bps,
        "slippage_bps": slippage_bps,
        "max_exposure_fraction": max_exposure_fraction,
    }
    import math
    for name, value in numeric_parameters.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{name} must be finite")
    if initial_cash <= 0:
        raise ValueError("initial_cash must be positive")
    if fee_bps < 0 or slippage_bps < 0:
        raise ValueError("fee_bps and slippage_bps must be non-negative")
    if not 0 < max_exposure_fraction <= 1:
        raise ValueError("max_exposure_fraction must be in (0, 1]")
    reports: dict[str, Any] = {}
    for dataset_id, candles in datasets.items():
        if not isinstance(dataset_id, str) or not dataset_id.strip():
            raise ValueError("dataset identifiers must be non-empty strings")
        walk = evaluate_baseline_walk_forward(
            candles,
            initial_train_bars=initial_train_bars,
            test_bars=test_bars,
            step_bars=step_bars,
            initial_cash=initial_cash,
            fee_bps=fee_bps,
            slippage_bps=slippage_bps,
            max_exposure_fraction=max_exposure_fraction,
        )
        resolved_step = test_bars if step_bars is None else step_bars
        continuous_oos = None
        monte_carlo = {
            "status": "SKIPPED_NON_CONTIGUOUS_TEST_WINDOWS",
            "note": "Monte Carlo requires a continuous out-of-sample equity path; test windows contain gaps.",
        }
        if resolved_step == test_bars:
            signals = generate_sma_trend_signals(candles)
            oos_candles = candles[initial_train_bars:]
            entries = signals["entry_signals"][initial_train_bars:]
            exits = signals["exit_signals"][initial_train_bars:]
            if signals["bullish_condition"][initial_train_bars]:
                entries[0] = True
            continuous_oos = run_long_only_backtest(
                oos_candles,
                entries,
                exits,
                initial_cash=initial_cash,
                fee_bps=fee_bps,
                slippage_bps=slippage_bps,
                max_exposure_fraction=max_exposure_fraction,
            )
            monte_carlo = bootstrap_trade_returns(
                continuous_oos["trades"],
                simulations=simulations,
                seed=seed,
                initial_equity=initial_cash,
                minimum_trades=minimum_trades,
            )
        continuous_trades = (
            continuous_oos["trades"] if continuous_oos is not None else None
        )
        reports[dataset_id] = {
            "dataset_id": dataset_id,
            "walk_forward": walk,
            "continuous_oos": continuous_oos,
            "monte_carlo": monte_carlo,
            "trade_count_consistent": (
                len(continuous_trades) == walk["closed_trades"]
                if continuous_trades is not None
                else None
            ),
        }
    return {
        "method": "per_dataset_walk_forward_with_continuous_oos_when_windows_are_adjacent",
        "research_only": True,
        "pooled_assets_or_timeframes": False,
        "dataset_count": len(reports),
        "parameters": {
            "initial_train_bars": initial_train_bars,
            "test_bars": test_bars,
            "step_bars": step_bars,
            "initial_cash": initial_cash,
            "fee_bps": fee_bps,
            "slippage_bps": slippage_bps,
            "max_exposure_fraction": max_exposure_fraction,
            "simulations": simulations,
            "seed": seed,
            "minimum_trades_for_monte_carlo": minimum_trades,
        },
        "reports": reports,
        "limitations": [
            "Each dataset is evaluated independently; results are not pooled",
            "Continuous out-of-sample portfolio starts flat at the first test bar and remains invested across adjacent test-window boundaries",
            "Monte Carlo resamples closed trades from the continuous out-of-sample portfolio only; skipped when test windows have gaps",
            "Bootstrap assumes exchangeability and does not preserve trade order or dependence",
            "No report is evidence of future profitability",
        ],
    }
