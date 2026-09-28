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
    """Research-only bootstrap of observed closed-trade returns, not a forecast."""
    if isinstance(simulations, bool) or not isinstance(simulations, int) or simulations < 100:
        raise ValueError("simulations must be an integer >= 100")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    if not math.isfinite(initial_equity) or initial_equity <= 0:
        raise ValueError("initial_equity must be finite and positive")
    if isinstance(minimum_trades, bool) or not isinstance(minimum_trades, int) or minimum_trades < 1:
        raise ValueError("minimum_trades must be a positive integer")
    returns = []
    for i, trade in enumerate(trades):
        value = trade.get("return_pct")
        if isinstance(value, bool):
            raise ValueError(f"trade {i} return_pct must be finite")
        try:
            value = float(value)
        except (TypeError, ValueError, OverflowError):
            raise ValueError(f"trade {i} return_pct must be finite") from None
        if not math.isfinite(value) or value <= -100:
            raise ValueError(f"trade {i} return_pct must be > -100 and finite")
        returns.append(value / 100)
    if len(returns) < minimum_trades:
        return {"method": "trade_return_bootstrap_with_replacement", "research_only": True,
                "status": "INSUFFICIENT_TRADES", "closed_trades": len(returns),
                "minimum_trades": minimum_trades, "simulations": 0, "seed": seed, "results": None}
    rng = random.Random(seed)
    finals, drawdowns = [], []
    for _ in range(simulations):
        equity = peak = initial_equity
        max_dd = 0.0
        for _ in returns:
            equity *= 1 + rng.choice(returns)
            peak = max(peak, equity)
            max_dd = max(max_dd, (peak - equity) / peak if peak else 0.0)
        finals.append(equity)
        drawdowns.append(max_dd)
    finals.sort()
    drawdowns.sort()
    def pct(values, q):
        return values[min(len(values) - 1, int((len(values) - 1) * q))]
    return {
        "method": "trade_return_bootstrap_with_replacement",
        "research_only": True,
        "status": "ESTIMATE_ONLY_NOT_A_FORECAST",
        "closed_trades": len(returns),
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
        "limitations": ["Resamples observed trade returns only",
                        "Does not model serial dependence or regime change",
                        "Not evidence of future profitability"],
    }
