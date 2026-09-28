import asyncio

import httpx

from backend.app.data.base import MarketDataResult
from backend.app.data.crypto_spot import (
    FallbackCryptoSpotMarketDataProvider,
    OkxSpotMarketDataProvider,
)


def okx_row(ts_ms, *, confirm="1", close="102"):
    return [str(ts_ms), "100", "105", "95", close, "12", "1200", "1200", confirm]


def test_okx_provider_parses_only_confirmed_candles():
    now = 1_700_000_000.0
    rows = [
        okx_row((now - 7200) * 1000),
        okx_row((now - 3600) * 1000),
        okx_row(now * 1000, confirm="0"),
    ]

    def handler(request):
        assert request.url.path == "/api/v5/market/candles"
        assert request.url.params["instId"] == "BTC-USDT"
        assert request.url.params["bar"] == "1H"
        assert request.url.params["limit"] == "300"
        return httpx.Response(200, json={"code": "0", "data": rows})

    provider = OkxSpotMarketDataProvider(
        transport=httpx.MockTransport(handler),
        clock=lambda: now,
    )
    result = asyncio.run(
        provider.get_market_data("crypto_spot", "BTCUSDT", "1d")
    )

    assert result.available is True
    assert result.fresh is True
    assert result.complete is False
    assert len(result.data["candles"]) == 2
    assert result.source == "okx_spot"


def test_okx_provider_rejects_unsupported_symbol_format():
    provider = OkxSpotMarketDataProvider(clock=lambda: 1_700_000_000)
    result = asyncio.run(
        provider.get_market_data("crypto_spot", "BTC-PERP", "1d")
    )

    assert result.available is False
    assert result.issues == ["unsupported_symbol_format"]


def test_crypto_fallback_uses_okx_when_binance_is_unavailable():
    class FailedPrimary:
        async def get_market_data(self, market, symbol, horizon):
            return MarketDataResult(
                False, False, False, {}, "binance_spot", ["exchange_http_451"]
            )

    class WorkingFallback:
        async def get_market_data(self, market, symbol, horizon):
            return MarketDataResult(
                True,
                True,
                True,
                {"candles": [{"close": 100}]},
                "okx_spot",
                [],
            )

    provider = FallbackCryptoSpotMarketDataProvider(
        primary=FailedPrimary(),
        fallback=WorkingFallback(),
    )
    result = asyncio.run(
        provider.get_market_data("crypto_spot", "BTCUSDT", "1d")
    )

    assert result.available is True
    assert result.source == "okx_spot"


def test_crypto_fallback_uses_secondary_when_primary_history_is_incomplete():
    class IncompletePrimary:
        async def get_market_data(self, market, symbol, horizon):
            return MarketDataResult(
                True,
                True,
                False,
                {"candles": []},
                "binance_spot",
                ["insufficient_history_for_indicators"],
            )

    class WorkingFallback:
        async def get_market_data(self, market, symbol, horizon):
            return MarketDataResult(
                True, True, True, {"candles": [1]}, "okx_spot", []
            )

    provider = FallbackCryptoSpotMarketDataProvider(
        primary=IncompletePrimary(),
        fallback=WorkingFallback(),
    )
    result = asyncio.run(
        provider.get_market_data("crypto_spot", "BTCUSDT", "1d")
    )

    assert result.available is True
    assert result.source == "okx_spot"


def test_crypto_fallback_fails_closed_when_both_sources_fail():
    class Failed:
        async def get_market_data(self, market, symbol, horizon):
            return MarketDataResult(
                False, False, False, {}, "failed", ["unavailable"]
            )

    provider = FallbackCryptoSpotMarketDataProvider(
        primary=Failed(),
        fallback=Failed(),
    )
    result = asyncio.run(
        provider.get_market_data("crypto_spot", "BTCUSDT", "1d")
    )

    assert result.available is False
    assert result.issues == ["primary_unavailable", "fallback_unavailable"]
