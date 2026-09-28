from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from ..data.validation import validate_ohlcv


def run_long_only_backtest(
    candles: Sequence[Mapping[str, Any]],
    entry_signals: Sequence[bool],
    exit_signals: Sequence[bool],
    *,
    initial_cash: float = 100_000.0,
    fee_bps: float = 10.0,
    slippage_bps: float = 5.0,
    max_exposure_fraction: float = 0.95,
) -> dict[str, Any]:
    """Backtest close-generated signals at the following candle's open.

    Long-only, one position at a time, no leverage, explicit fees/slippage.
    A signal on the final candle is not filled because no next open exists.
    Open positions are marked to the final close, not silently liquidated.
    Realized PnL includes closed trades only; open capital is not a loss.
    """
    if not candles:
        raise ValueError("candles must not be empty")
    if len(entry_signals) != len(candles) or len(exit_signals) != len(candles):
        raise ValueError("signal arrays must match candle count")
    if not all(isinstance(value, bool) for value in entry_signals):
        raise ValueError("entry_signals must contain booleans")
    if not all(isinstance(value, bool) for value in exit_signals):
        raise ValueError("exit_signals must contain booleans")
    if not math.isfinite(initial_cash) or initial_cash <= 0:
        raise ValueError("initial_cash must be finite and positive")
    if not math.isfinite(fee_bps) or not 0 <= fee_bps < 10_000:
        raise ValueError("fee_bps must be in [0, 10000)")
    if not math.isfinite(slippage_bps) or not 0 <= slippage_bps < 10_000:
        raise ValueError("slippage_bps must be in [0, 10000)")
    if (
        not math.isfinite(max_exposure_fraction)
        or not 0 < max_exposure_fraction <= 1
    ):
        raise ValueError("max_exposure_fraction must be in (0, 1]")

    last_timestamp = float(candles[-1]["timestamp"])
    checked = validate_ohlcv(candles, now=last_timestamp + 1)
    if not checked["valid"] or not checked["complete"]:
        raise ValueError("invalid or incomplete candles: " + ", ".join(checked["issues"]))
    series = checked["candles"]

    fee_rate = fee_bps / 10_000
    slippage_rate = slippage_bps / 10_000
    cash = float(initial_cash)
    position: dict[str, Any] | None = None
    pending_action: str | None = None
    trades: list[dict[str, Any]] = []
    equity_curve: list[dict[str, float]] = []
    peak_equity = cash
    max_drawdown = 0.0
    fees_total = 0.0

    for index, candle in enumerate(series):
        if pending_action == "entry" and position is None:
            execution_price = candle["open"] * (1 + slippage_rate)
            budget = cash * max_exposure_fraction
            units = budget / (execution_price * (1 + fee_rate))
            gross_cost = units * execution_price
            entry_fee = gross_cost * fee_rate
            total_cost = gross_cost + entry_fee
            if units > 0 and total_cost <= cash + 1e-9:
                cash -= total_cost
                fees_total += entry_fee
                position = {
                    "entry_index": index,
                    "entry_timestamp": candle["timestamp"],
                    "entry_price": execution_price,
                    "units": units,
                    "entry_fee": entry_fee,
                    "entry_cost": total_cost,
                }

        elif pending_action == "exit" and position is not None:
            execution_price = candle["open"] * (1 - slippage_rate)
            gross_proceeds = position["units"] * execution_price
            exit_fee = gross_proceeds * fee_rate
            net_proceeds = gross_proceeds - exit_fee
            cash += net_proceeds
            fees_total += exit_fee
            net_pnl = net_proceeds - position["entry_cost"]
            trades.append(
                {
                    "entry_index": position["entry_index"],
                    "exit_index": index,
                    "entry_timestamp": position["entry_timestamp"],
                    "exit_timestamp": candle["timestamp"],
                    "entry_price": position["entry_price"],
                    "exit_price": execution_price,
                    "units": position["units"],
                    "entry_fee": position["entry_fee"],
                    "exit_fee": exit_fee,
                    "net_pnl": net_pnl,
                    "return_pct": net_pnl / position["entry_cost"] * 100,
                }
            )
            position = None

        pending_action = None
        equity = cash + (
            position["units"] * candle["close"] if position is not None else 0.0
        )
        peak_equity = max(peak_equity, equity)
        drawdown = (peak_equity - equity) / peak_equity if peak_equity else 0.0
        max_drawdown = max(max_drawdown, drawdown)
        equity_curve.append(
            {
                "timestamp": candle["timestamp"],
                "cash": cash,
                "equity": equity,
            }
        )

        if index < len(series) - 1:
            if position is not None and exit_signals[index]:
                pending_action = "exit"
            elif position is None and entry_signals[index]:
                pending_action = "entry"

    final_equity = equity_curve[-1]["equity"]
    wins = sum(1 for trade in trades if trade["net_pnl"] > 0)
    realized_pnl = sum(trade["net_pnl"] for trade in trades)
    gross_profit = sum(trade["net_pnl"] for trade in trades if trade["net_pnl"] > 0)
    gross_loss = -sum(trade["net_pnl"] for trade in trades if trade["net_pnl"] < 0)
    losses = len(trades) - wins
    average_trade_return_pct = (
        sum(trade["return_pct"] for trade in trades) / len(trades)
        if trades else None
    )
    average_win = gross_profit / wins if wins else None
    average_loss = -gross_loss / losses if losses else None
    profit_factor = (
        gross_profit / gross_loss if gross_loss > 0
        else (None if gross_profit == 0 else math.inf)
    )
    expectancy = realized_pnl / len(trades) if trades else None
    open_position = None
    if position is not None:
        mark_value = position["units"] * series[-1]["close"]
        open_position = {
            "entry_index": position["entry_index"],
            "entry_timestamp": position["entry_timestamp"],
            "entry_price": position["entry_price"],
            "units": position["units"],
            "unrealized_pnl": mark_value - position["entry_cost"],
        }

    return {
        "initial_cash": initial_cash,
        "cash_balance": cash,
        "cash_balance_pct": cash / initial_cash * 100,
        "final_equity": final_equity,
        "total_return_pct": (final_equity / initial_cash - 1) * 100,
        "realized_pnl": realized_pnl,
        "realized_return_pct": realized_pnl / initial_cash * 100,
        "max_drawdown_pct": max_drawdown * 100,
        "closed_trades": len(trades),
        "wins": wins,
        "losses": losses,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": profit_factor,
        "average_win": average_win,
        "average_loss": average_loss,
        "expectancy_per_trade": expectancy,
        "average_trade_return_pct": average_trade_return_pct,
        "win_rate_pct": wins / len(trades) * 100 if trades else None,
        "fees_total": fees_total,
        "trades": trades,
        "open_position": open_position,
        "equity_curve": equity_curve,
        "execution_model": "signal_at_close_filled_at_next_open",
    }
