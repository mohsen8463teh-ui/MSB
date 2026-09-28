import pytest

from backend.app.backtest.holdout import evaluate_baseline_holdout


def rising_candles(count=300):
    rows = []
    for index in range(count):
        close = 100.0 + index
        rows.append(
            {
                "timestamp": 1_000_000.0 + index * 86400,
                "open": close - 0.2,
                "high": close + 0.5,
                "low": close - 0.5,
                "close": close,
                "volume": 100.0,
            }
        )
    return rows


def test_holdout_uses_prior_history_for_warmup_but_fills_inside_test_only():
    result = evaluate_baseline_holdout(
        rising_candles(),
        split_index=240,
        initial_cash=1000,
        fee_bps=0,
        slippage_bps=0,
        max_exposure_fraction=1,
    )

    assert result["method"] == "fixed_chronological_holdout"
    assert result["training_period_used_for_parameter_fitting"] is False
    assert result["train_bars"] == 240
    assert result["test_bars"] == 60
    assert result["sample_status"] == "INSUFFICIENT_TRADES"
    assert result["minimum_closed_trades_for_screening"] == 30
    assert result["results"]["open_position"]["entry_index"] == 1
    assert result["results"]["closed_trades"] == 0


@pytest.mark.parametrize("split_index", [199, 299, True, "200"])
def test_holdout_rejects_invalid_split(split_index):
    with pytest.raises(ValueError):
        evaluate_baseline_holdout(rising_candles(), split_index=split_index)
