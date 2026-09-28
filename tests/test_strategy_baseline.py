from backend.app.analysis.strategy_baseline import generate_sma_trend_signals
from backend.app.backtest.engine import run_long_only_backtest


def candles_from_closes(closes):
    rows = []
    for index, close in enumerate(closes):
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


def test_baseline_emits_only_boolean_long_flags_after_warmup():
    closes = [100.0 + index for index in range(240)]
    result = generate_sma_trend_signals(candles_from_closes(closes))

    assert result["strategy_id"] == "sma_trend_baseline_v1"
    assert result["research_only"] is True
    assert not any(result["entry_signals"][:199])
    assert len(result["entry_signals"]) == len(closes)
    assert all(type(flag) is bool for flag in result["entry_signals"])
    assert sum(result["entry_signals"]) == 1
    assert sum(result["exit_signals"]) == 0


def test_baseline_has_no_lookahead_for_earlier_signal_values():
    closes = [100.0 + index for index in range(260)]
    original = candles_from_closes(closes)
    changed = candles_from_closes(closes)
    for index in range(240, 260):
        changed[index]["open"] = 10_000.0
        changed[index]["high"] = 10_001.0
        changed[index]["low"] = 9_999.0
        changed[index]["close"] = 10_000.0

    first = generate_sma_trend_signals(original)
    second = generate_sma_trend_signals(changed)

    assert first["entry_signals"][:240] == second["entry_signals"][:240]
    assert first["exit_signals"][:240] == second["exit_signals"][:240]


def test_baseline_signals_are_filled_only_at_next_open():
    rows = candles_from_closes([100.0 + index for index in range(220)])
    signals = generate_sma_trend_signals(rows)
    result = run_long_only_backtest(
        rows,
        signals["entry_signals"],
        signals["exit_signals"],
        initial_cash=1000,
        fee_bps=0,
        slippage_bps=0,
        max_exposure_fraction=1,
    )

    entry_signal_index = signals["entry_signals"].index(True)
    assert result["open_position"]["entry_index"] == entry_signal_index + 1
    assert result["execution_model"] == "signal_at_close_filled_at_next_open"


def test_baseline_rejects_short_history():
    import pytest

    with pytest.raises(ValueError, match="at least 200"):
        generate_sma_trend_signals(candles_from_closes([100.0 + i for i in range(100)]))
