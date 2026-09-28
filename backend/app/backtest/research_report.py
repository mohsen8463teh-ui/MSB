from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

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
        trades = [
            trade
            for fold in walk["folds"]
            for trade in fold["results"]["trades"]
        ]
        monte_carlo = bootstrap_trade_returns(
            trades,
            simulations=simulations,
            seed=seed,
            initial_equity=initial_cash,
            minimum_trades=minimum_trades,
        )
        reports[dataset_id] = {
            "dataset_id": dataset_id,
            "walk_forward": walk,
            "monte_carlo": monte_carlo,
            "trade_count_consistent": len(trades) == walk["closed_trades"],
        }
    return {
        "method": "per_dataset_walk_forward_plus_trade_pnl_bootstrap",
        "research_only": True,
        "pooled_assets_or_timeframes": False,
        "dataset_count": len(reports),
        "reports": reports,
        "limitations": [
            "Each dataset is evaluated independently; results are not pooled",
            "Monte Carlo resamples only closed trades from walk-forward test folds",
            "Bootstrap assumes exchangeability and does not preserve trade order or dependence",
            "No report is evidence of future profitability",
        ],
    }
