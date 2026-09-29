import pytest

from backend.app.backtest.research_report import evaluate_research_universe


def rising_candles(count=500):
    rows = []
    for i in range(count):
        close = 100.0 + i
        rows.append({"timestamp": 1_000_000.0 + i * 86400, "open": close - .2,
                     "high": close + .5, "low": close - .5, "close": close, "volume": 100.0})
    return rows


def test_research_report_keeps_datasets_separate_and_marks_small_samples():
    result = evaluate_research_universe(
        {"BTC:1d": rising_candles(), "ETH:1d": rising_candles()},
        initial_train_bars=300, test_bars=80, fee_bps=0, slippage_bps=0,
        simulations=100,
    )
    assert result["pooled_assets_or_timeframes"] is False
    assert result["dataset_count"] == 2
    assert set(result["reports"]) == {"BTC:1d", "ETH:1d"}
    for report in result["reports"].values():
        assert report["trade_count_consistent"] is True
        assert report["monte_carlo"]["status"] == "INSUFFICIENT_TRADES"


@pytest.mark.parametrize("datasets", [{}, None, []])
def test_rejects_empty_datasets(datasets):
    with pytest.raises(ValueError):
        evaluate_research_universe(datasets)



def test_research_report_uses_continuous_oos_equity_not_sum_of_reset_folds():
    report = evaluate_research_universe(
        {"BTC:1d": rising_candles()},
        initial_train_bars=300,
        test_bars=80,
        fee_bps=0,
        slippage_bps=0,
        simulations=100,
    )["reports"]["BTC:1d"]

    oos = report["continuous_oos"]
    assert oos is not None
    assert len(oos["equity_curve"]) == 200
    assert oos["final_equity"] - oos["initial_cash"] == pytest.approx(
        oos["realized_pnl"]
        + (oos["open_position"]["unrealized_pnl"] if oos["open_position"] else 0)
    )
    assert report["monte_carlo"]["status"] == "INSUFFICIENT_TRADES"


def test_research_report_skips_monte_carlo_for_gapped_test_windows():
    report = evaluate_research_universe(
        {"BTC:1d": rising_candles()},
        initial_train_bars=300,
        test_bars=80,
        step_bars=100,
        simulations=100,
    )["reports"]["BTC:1d"]

    assert report["continuous_oos"] is None
    assert report["monte_carlo"]["status"] == "SKIPPED_NON_CONTIGUOUS_TEST_WINDOWS"
