import pytest

from backend.app.backtest.engine import run_long_only_backtest


def candles(opens, closes):
    rows = []
    for index, (open_price, close) in enumerate(zip(opens, closes)):
        rows.append(
            {
                "timestamp": 1_000_000.0 + index * 86400,
                "open": float(open_price),
                "high": float(max(open_price, close) + 1),
                "low": float(min(open_price, close) - 1),
                "close": float(close),
                "volume": 100.0,
            }
        )
    return rows


def test_signals_execute_at_next_open_not_same_close():
    result = run_long_only_backtest(
        candles([100, 110, 120], [105, 115, 125]),
        [True, False, False],
        [False, True, False],
        initial_cash=1000,
        fee_bps=0,
        slippage_bps=0,
        max_exposure_fraction=1,
    )

    assert result["closed_trades"] == 1
    trade = result["trades"][0]
    assert trade["entry_index"] == 1
    assert trade["entry_price"] == 110
    assert trade["exit_index"] == 2
    assert trade["exit_price"] == 120
    assert trade["net_pnl"] == pytest.approx(1000 / 110 * 10)


def test_final_bar_signal_is_not_filled_without_next_open():
    result = run_long_only_backtest(
        candles([100, 105], [101, 106]),
        [False, True],
        [False, False],
        initial_cash=1000,
        fee_bps=0,
        slippage_bps=0,
    )

    assert result["closed_trades"] == 0
    assert result["open_position"] is None
    assert result["final_equity"] == 1000


def test_fees_slippage_and_exposure_never_make_cash_negative():
    result = run_long_only_backtest(
        candles([100, 110, 120], [105, 115, 125]),
        [True, False, False],
        [False, True, False],
        initial_cash=1000,
        fee_bps=20,
        slippage_bps=10,
        max_exposure_fraction=0.8,
    )

    assert all(point["cash"] >= -1e-8 for point in result["equity_curve"])
    assert result["fees_total"] > 0
    assert result["trades"][0]["entry_price"] > 110
    assert result["trades"][0]["exit_price"] < 120


def test_rejects_overlapping_signal_shapes_and_invalid_parameters():
    rows = candles([100, 101], [100, 101])

    with pytest.raises(ValueError, match="signal arrays"):
        run_long_only_backtest(rows, [True], [False])

    with pytest.raises(ValueError, match="max_exposure_fraction"):
        run_long_only_backtest(
            rows,
            [False, False],
            [False, False],
            max_exposure_fraction=1.5,
        )


def test_open_position_is_marked_not_force_closed():
    result = run_long_only_backtest(
        candles([100, 105, 110], [101, 108, 115]),
        [True, False, False],
        [False, False, False],
        initial_cash=1000,
        fee_bps=0,
        slippage_bps=0,
        max_exposure_fraction=1,
    )

    assert result["closed_trades"] == 0
    assert result["open_position"] is not None
    assert result["open_position"]["entry_index"] == 1
    assert result["final_equity"] > result["realized_cash"]
