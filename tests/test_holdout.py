import pytest

from backend.app.backtest.holdout import evaluate_baseline_holdout, evaluate_baseline_walk_forward


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


def test_walk_forward_creates_chronological_non_overlapping_folds():
    result = evaluate_baseline_walk_forward(
        rising_candles(500),
        initial_train_bars=300,
        test_bars=80,
        fee_bps=0,
        slippage_bps=0,
    )

    assert result["method"] == "expanding_window_walk_forward"
    assert result["fold_count"] == 3
    assert result["overlapping_test_windows"] is False
    assert result["parameters_fitted"] is False
    assert result["folds"][0]["test_bars"] == 80
    assert result["folds"][1]["test_start_timestamp"] > result["folds"][0]["test_end_timestamp"]
    assert result["folds"][2]["test_bars"] == 40


@pytest.mark.parametrize(
    "kwargs",
    [
        {"initial_train_bars": 199},
        {"test_bars": 1},
        {"test_bars": 80, "step_bars": 79},
    ],
)
def test_walk_forward_rejects_invalid_window_configuration(kwargs):
    with pytest.raises(ValueError):
        evaluate_baseline_walk_forward(rising_candles(500), **kwargs)
