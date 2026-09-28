from __future__ import annotations

import math
import random
from collections.abc import Mapping, Sequence
from typing import Any


def bootstrap_trade_returns(
    trades: Sequence[Mapping[str, Any]],
    *,
    simulations: int = 2_000,
    seed: int = 7,
    initial_equity: float = 100_000.0,
    minimum_trades: int = 30,
) -> dict[str, Any]:
    """Research-only bootstrap of observed closed-trade PnL, not a forecast.

    PnL is added to equity (not compounded as a percentage of position cost):
    engine return_pct is measured against position entry cost, not total account
    equity. This fixed-dollar resampling is a diagnostic, not a sizing model.
    """
    if isinstance(simulations, bool) or not isinstance(simulations, int) or simulations < 100:
        raise ValueError("simulations must be an integer >= 100")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    if isinstance(initial_equity, bool) or not math.isfinite(initial_equity) or initial_equity <= 0:
        raise ValueError("initial_equity must be finite and positive")
    if isinstance(minimum_trades, bool) or not isinstance(minimum_trades, int) or minimum_trades < 1:
        raise ValueError("minimum_trades must be a positive integer")
    pnls = []
    for i, trade in enumerate(trades):
        value = trade.get("net_pnl")
        if isinstance(value, bool):
            raise ValueError(f"trade {i} net_pnl must be finite")
        try:
            value = float(value)
        except (TypeError, ValueError, OverflowError):
            raise ValueError(f"trade {i} net_pnl must be finite") from None
        if not math.isfinite(value):
            raise ValueError(f"trade {i} net_pnl must be finite")
        pnls.append(value)
    if len(pnls) < minimum_trades:
        return {"method": "fixed_dollar_trade_pnl_bootstrap", "research_only": True,
                "status": "INSUFFICIENT_TRADES", "closed_trades": len(pnls),
                "minimum_trades": minimum_trades, "simulations": 0, "seed": seed, "results": None}
    rng = random.Random(seed)
    finals, drawdowns = [], []
    for _ in range(simulations):
        equity = peak = initial_equity
        max_dd = 0.0
        for _ in pnls:
            equity += rng.choice(pnls)
            peak = max(peak, equity)
            max_dd = max(max_dd, (peak - equity) / peak if peak > 0 else 1.0)
        finals.append(equity)
        drawdowns.append(max_dd)
    finals.sort()
    drawdowns.sort()
    def pct(values, q):
        return values[min(len(values) - 1, int((len(values) - 1) * q))]
    return {
        "method": "fixed_dollar_trade_pnl_bootstrap",
        "research_only": True,
        "status": "ESTIMATE_ONLY_NOT_A_FORECAST",
        "closed_trades": len(pnls),
        "minimum_trades": minimum_trades,
        "simulations": simulations,
        "seed": seed,
        "results": {
            "final_equity_p05": pct(finals, .05),
            "final_equity_median": pct(finals, .50),
            "final_equity_p95": pct(finals, .95),
            "max_drawdown_p50_pct": pct(drawdowns, .50) * 100,
            "max_drawdown_p95_pct": pct(drawdowns, .95) * 100,
            "probability_of_loss_pct": sum(x < initial_equity for x in finals) / simulations * 100,
        },
        "limitations": ["Resamples observed closed-trade dollar PnL with replacement",
                        "Assumes fixed-dollar PnL per resampled trade; does not model account-based resizing",
                        "Does not model serial dependence or regime change",
                        "Not evidence of future profitability"],
    }
