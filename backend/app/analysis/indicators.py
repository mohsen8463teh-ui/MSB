from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..data.validation import validate_ohlcv


def _sma(values: list[float], period: int) -> float:
    return sum(values[-period:]) / period


def _wilder_average(values: list[float], period: int) -> float:
    if len(values) < period:
        raise ValueError(f"at least {period} values are required")
    average = sum(values[:period]) / period
    for value in values[period:]:
        average = (average * (period - 1) + value) / period
    return average


def _rsi(closes: list[float], period: int = 14) -> float:
    changes = [
        closes[index] - closes[index - 1]
        for index in range(1, len(closes))
    ]
    gains = [max(change, 0.0) for change in changes]
    losses = [max(-change, 0.0) for change in changes]
    average_gain = _wilder_average(gains, period)
    average_loss = _wilder_average(losses, period)
    if average_loss == 0:
        return 100.0 if average_gain > 0 else 50.0
    relative_strength = average_gain / average_loss
    return 100.0 - (100.0 / (1.0 + relative_strength))


def _atr(candles: list[dict[str, float]], period: int = 14) -> float:
    true_ranges = []
    for index in range(1, len(candles)):
        current = candles[index]
        previous_close = candles[index - 1]["close"]
        true_ranges.append(
            max(
                current["high"] - current["low"],
                abs(current["high"] - previous_close),
                abs(current["low"] - previous_close),
            )
        )
    return _wilder_average(true_ranges, period)


def calculate_indicators(
    candles: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Calculate closed-candle indicators; never creates a trade decision."""
    if not candles:
        raise ValueError("at least 200 validated candles are required")

    last_timestamp = float(candles[-1]["timestamp"])
    checked = validate_ohlcv(candles, now=last_timestamp + 1)
    if not checked["valid"]:
        raise ValueError("invalid candle series: " + ", ".join(checked["issues"]))

    series = checked["candles"]
    if len(series) < 200:
        raise ValueError("at least 200 validated candles are required")

    closes = [item["close"] for item in series]
    volumes = [item["volume"] for item in series]
    current = series[-1]
    prior_20 = series[-21:-1]
    sma20 = _sma(closes, 20)
    sma50 = _sma(closes, 50)
    sma200 = _sma(closes, 200)
    rsi14 = _rsi(closes, 14)
    atr14 = _atr(series, 14)
    momentum20 = current["close"] / closes[-21] - 1
    momentum60 = current["close"] / closes[-61] - 1
    volume_baseline = sum(volumes[-21:-1]) / 20
    volume_ratio = (
        current["volume"] / volume_baseline if volume_baseline > 0 else None
    )
    resistance20 = max(item["high"] for item in prior_20)
    support20 = min(item["low"] for item in prior_20)
    bullish_alignment = sma20 > sma50 > sma200

    if current["close"] > sma200 and sma50 > sma200 and momentum60 > 0:
        regime = "BULLISH_TREND"
    elif current["close"] < sma200 and sma50 < sma200 and momentum60 < 0:
        regime = "BEARISH_TREND"
    else:
        regime = "RANGE_OR_MIXED"

    if momentum20 > 0 and momentum60 > 0:
        momentum_state = "POSITIVE"
    elif momentum20 < 0 and momentum60 < 0:
        momentum_state = "NEGATIVE"
    else:
        momentum_state = "MIXED"

    rsi_state = "OVERBOUGHT" if rsi14 >= 70 else "OVERSOLD" if rsi14 <= 30 else "NEUTRAL"
    volume_state = (
        "UNKNOWN"
        if volume_ratio is None
        else "ELEVATED"
        if volume_ratio >= 1.5
        else "LOW"
        if volume_ratio <= 0.7
        else "NORMAL"
    )

    return {
        "close": current["close"],
        "sma20": sma20,
        "sma50": sma50,
        "sma200": sma200,
        "rsi14": rsi14,
        "atr14": atr14,
        "atr_percent": atr14 / current["close"] * 100,
        "momentum20": momentum20,
        "momentum60": momentum60,
        "momentum_state": momentum_state,
        "volume_ratio20": volume_ratio,
        "volume_state": volume_state,
        "support20": support20,
        "resistance20": resistance20,
        "breakout20": current["close"] > resistance20,
        "price_above_sma20": current["close"] > sma20,
        "price_above_sma50": current["close"] > sma50,
        "price_above_sma200": current["close"] > sma200,
        "trend_alignment_bullish": bullish_alignment,
        "market_regime": regime,
        "rsi_state": rsi_state,
        "candles_used": len(series),
    }
