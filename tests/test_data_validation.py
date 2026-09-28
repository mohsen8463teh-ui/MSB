import pytest

from backend.app.data.validation import validate_ohlcv


def candle(timestamp, *, open_=100, high=105, low=95, close=102, volume=10):
    return {
        "timestamp": timestamp,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    }


def test_valid_ohlcv_is_normalized_and_accepted():
    result = validate_ohlcv(
        [candle(100), candle(160)],
        interval_seconds=60,
        now=200,
    )

    assert result["valid"] is True
    assert result["complete"] is True
    assert len(result["candles"]) == 2
    assert result["candles"][0]["close"] == 102.0


@pytest.mark.parametrize(
    "bad",
    [
        candle(100, low=0),
        candle(100, high=90),
        candle(100, volume=-1),
        candle(100, close=float("nan")),
        candle(100, open_=0),
    ],
)
def test_invalid_prices_or_volume_are_rejected(bad):
    result = validate_ohlcv([bad], now=200)

    assert result["valid"] is False
    assert result["complete"] is False


def test_duplicate_and_out_of_order_timestamps_are_rejected():
    result = validate_ohlcv([candle(100), candle(100)], now=200)

    assert result["valid"] is False
    assert "candle_1_timestamp_not_strictly_increasing" in result["issues"]


def test_future_candle_is_rejected():
    result = validate_ohlcv([candle(201)], now=200)

    assert result["valid"] is False
    assert "candle_0_timestamp_in_future" in result["issues"]


def test_expected_interval_gap_marks_data_incomplete():
    result = validate_ohlcv(
        [candle(100), candle(220)],
        interval_seconds=60,
        now=300,
    )

    assert result["valid"] is True
    assert result["complete"] is False
    assert "gap_before_candle_1" in result["issues"]


def test_empty_input_fails_closed():
    result = validate_ohlcv([], now=200)

    assert result == {
        "valid": False,
        "complete": False,
        "candles": [],
        "issues": ["no_candles"],
    }


@pytest.mark.parametrize("bad_interval", [0, -1, True, False, 1.5, "60"])
def test_invalid_interval_configuration_is_rejected(bad_interval):
    with pytest.raises(ValueError, match="positive integer"):
        validate_ohlcv([candle(100)], interval_seconds=bad_interval, now=200)


@pytest.mark.parametrize("bad_now", [True, False, float("nan"), float("inf"), "200", None])
def test_invalid_explicit_clock_is_rejected(bad_now):
    if bad_now is None:
        return
    with pytest.raises(ValueError, match="finite numeric timestamp"):
        validate_ohlcv([candle(100)], now=bad_now)


def test_boolean_ohlcv_values_are_not_treated_as_numbers():
    result = validate_ohlcv([candle(100, close=True)], now=200)

    assert result["valid"] is False
    assert result["complete"] is False
    assert "candle_0_contains_non_finite_or_non_numeric_values" in result["issues"]
