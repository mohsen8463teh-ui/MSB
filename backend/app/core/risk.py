"""Risk-budget calculator for research; never creates or authorizes orders."""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class PositionSize:
    risk_budget: float
    risk_per_unit: float
    quantity_by_risk: float
    quantity_by_cash: float
    quantity: float
    notional: float
    estimated_loss_at_stop: float


def calculate_long_position_size(
    *, equity: float, risk_fraction: float, entry: float, stop: float,
    available_cash: float, max_exposure_fraction: float = 1.0,
) -> PositionSize:
    """Calculate a cash-capped LONG-only size; output is informational only."""
    values = (equity, risk_fraction, entry, stop, available_cash, max_exposure_fraction)
    if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) for v in values):
        raise ValueError("all_inputs_must_be_finite_numbers")
    if equity <= 0 or available_cash < 0:
        raise ValueError("equity_must_be_positive_and_cash_nonnegative")
    if not 0 < risk_fraction <= 1 or not 0 < max_exposure_fraction <= 1:
        raise ValueError("fractions_must_be_in_(0,1]")
    if entry <= 0 or stop <= 0 or stop >= entry:
        raise ValueError("long_stop_must_be_positive_and_below_entry")
    risk_budget = equity * risk_fraction
    per_unit = entry - stop
    by_risk = risk_budget / per_unit
    cash_cap = min(available_cash, equity * max_exposure_fraction)
    by_cash = cash_cap / entry
    quantity = min(by_risk, by_cash)
    notional = quantity * entry
    estimated_loss = quantity * per_unit
    derived = (risk_budget, per_unit, by_risk, cash_cap, by_cash, quantity, notional, estimated_loss)
    if any(not math.isfinite(value) for value in derived):
        raise ValueError("calculation_overflow")
    return PositionSize(
        risk_budget=risk_budget,
        risk_per_unit=per_unit,
        quantity_by_risk=by_risk,
        quantity_by_cash=by_cash,
        quantity=quantity,
        notional=notional,
        estimated_loss_at_stop=estimated_loss,
    )
