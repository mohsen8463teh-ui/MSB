import pytest

from backend.app.analysis.indicators import calculate_indicators


def rising_candles(count=220):
    candles = []
    for index in range(count):
        close = 100.0 + index
        candles.append(
            {
                "timestamp": 1_000_000.0 + index * 3600,
                "open": close - 0.2,
                "high": close + 0.5,
                "low": close - 0.5,
                "close": close,
                "volume": 10.0,
            }
        )
    return candles


def test_indicators_use_only_validated_closed_candles():
    result = calculate_indicators(rising_candles())

    assert result["candles_used"] == 220
    assert result["sma20"] == pytest.approx(309.5)
    assert result["sma50"] == pytest.approx(294.5)
    assert result["sma200"] == pytest.approx(219.5)
    assert result["rsi14"] == 100.0
    assert result["atr14"] > 0
    assert result["momentum20"] > 0
    assert result["momentum60"] > 0
    assert result["breakout20"] is True
    assert result["trend_alignment_bullish"] is True
    assert result["market_regime"] == "BULLISH_TREND"
    assert result["rsi_state"] == "OVERBOUGHT"


def test_indicators_refuse_insufficient_history():
    with pytest.raises(ValueError, match="at least 200"):
        calculate_indicators(rising_candles(199))


def test_indicators_refuse_invalid_ohlc():
    candles = rising_candles()
    candles[-1]["low"] = 0

    with pytest.raises(ValueError, match="invalid candle series"):
        calculate_indicators(candles)
