import math
import pytest

from backend.app.core.risk import calculate_long_position_size


def test_size_is_limited_by_risk_budget():
    result = calculate_long_position_size(
        equity=100_000, risk_fraction=0.01, entry=100, stop=95,
        available_cash=100_000,
    )
    assert result.quantity == pytest.approx(200)
    assert result.estimated_loss_at_stop == pytest.approx(1_000)


def test_size_is_capped_by_available_cash_and_exposure():
    result = calculate_long_position_size(
        equity=100_000, risk_fraction=0.5, entry=100, stop=90,
        available_cash=2_000, max_exposure_fraction=0.5,
    )
    assert result.quantity == pytest.approx(20)
    assert result.notional == pytest.approx(2_000)


@pytest.mark.parametrize("kwargs", [
    {"equity": 0, "risk_fraction": .01, "entry": 10, "stop": 9, "available_cash": 10},
    {"equity": 100, "risk_fraction": 0, "entry": 10, "stop": 9, "available_cash": 10},
    {"equity": 100, "risk_fraction": .01, "entry": 10, "stop": 10, "available_cash": 10},
    {"equity": 100, "risk_fraction": .01, "entry": 10, "stop": 11, "available_cash": 10},
    {"equity": 100, "risk_fraction": .01, "entry": 10, "stop": 9, "available_cash": -1},
    {"equity": math.inf, "risk_fraction": .01, "entry": 10, "stop": 9, "available_cash": 10},
])
def test_invalid_inputs_fail_closed(kwargs):
    with pytest.raises(ValueError):
        calculate_long_position_size(**kwargs)


def test_result_never_exceeds_either_cap():
    result = calculate_long_position_size(
        equity=1_000_000, risk_fraction=.02, entry=250, stop=225,
        available_cash=50_000, max_exposure_fraction=.1,
    )
    assert result.estimated_loss_at_stop <= result.risk_budget
    assert result.notional <= 50_000
