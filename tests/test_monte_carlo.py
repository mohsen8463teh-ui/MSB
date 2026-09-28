import pytest
from backend.app.backtest.monte_carlo import bootstrap_trade_returns

def sample(n, value=1.0):
    return [{"return_pct": value} for _ in range(n)]

def test_bootstrap_is_reproducible_and_not_a_forecast():
    a = bootstrap_trade_returns(sample(30), simulations=200, seed=42)
    assert a == bootstrap_trade_returns(sample(30), simulations=200, seed=42)
    assert a["status"] == "ESTIMATE_ONLY_NOT_A_FORECAST"
    assert a["results"]["probability_of_loss_pct"] == 0

def test_bootstrap_gates_insufficient_sample():
    result = bootstrap_trade_returns(sample(29), simulations=100)
    assert result["status"] == "INSUFFICIENT_TRADES"
    assert result["simulations"] == 0
    assert result["results"] is None

@pytest.mark.parametrize("kwargs", [{"simulations": 99}, {"simulations": True},
    {"seed": True}, {"initial_equity": 0}, {"minimum_trades": 0}])
def test_invalid_configuration_rejected(kwargs):
    with pytest.raises(ValueError):
        bootstrap_trade_returns(sample(30), **kwargs)

@pytest.mark.parametrize("value", [float("nan"), float("inf"), -100, True, None])
def test_invalid_trade_return_rejected(value):
    with pytest.raises(ValueError):
        bootstrap_trade_returns([{"return_pct": value}] * 30, simulations=100)
