import asyncio

import httpx

from backend.app.data.binance_spot import BinanceSpotMarketDataProvider


def make_row(open_ms, close_ms, price="100"):
    return [
        open_ms,
        price,
        "105",
        "95",
        "102",
        "12",
        close_ms,
        "0",
        1,
        "0",
        "0",
        "0",
    ]


def test_binance_provider_normalizes_closed_candles_and_excludes_open_bar():
    now = 1_700_000_000.0
    rows = [
        make_row((now - 7200) * 1000, (now - 3601) * 1000),
        make_row((now - 3600) * 1000, (now - 1) * 1000),
        make_row(now * 1000, (now + 3599) * 1000),
    ]

    def handler(request):
        assert request.url.path == "/api/v3/klines"
        assert request.url.params["symbol"] == "BTCUSDT"
        return httpx.Response(200, json=rows)

    provider = BinanceSpotMarketDataProvider(
        transport=httpx.MockTransport(handler),
        clock=lambda: now,
    )
    result = asyncio.run(
        provider.get_market_data("crypto_spot", "btcusdt", "1d")
    )

    assert result.available is True
    assert result.fresh is True
    assert len(result.data["candles"]) == 2
    assert result.data["symbol"] == "BTCUSDT"
    assert result.source == "binance_spot"


def test_provider_fails_closed_for_bad_symbol_or_horizon():
    provider = BinanceSpotMarketDataProvider(clock=lambda: 1_700_000_000)

    bad_symbol = asyncio.run(
        provider.get_market_data("crypto_spot", "BTC/USDT", "1d")
    )
    bad_horizon = asyncio.run(
        provider.get_market_data("crypto_spot", "BTCUSDT", "2w")
    )

    assert bad_symbol.available is False
    assert bad_symbol.issues == ["invalid_or_missing_symbol"]
    assert bad_horizon.available is False
    assert bad_horizon.issues == ["unsupported_or_missing_horizon"]


def test_provider_handles_exchange_error_without_raising():
    def handler(request):
        return httpx.Response(503)

    provider = BinanceSpotMarketDataProvider(
        transport=httpx.MockTransport(handler),
        clock=lambda: 1_700_000_000,
    )
    result = asyncio.run(
        provider.get_market_data("crypto_spot", "BTCUSDT", "1d")
    )

    assert result.available is False
    assert result.data == {}
    assert result.issues == ["market_data_request_failed"]


def test_provider_rejects_malformed_exchange_rows():
    def handler(request):
        return httpx.Response(200, json=[["bad"]])

    provider = BinanceSpotMarketDataProvider(
        transport=httpx.MockTransport(handler),
        clock=lambda: 1_700_000_000,
    )
    result = asyncio.run(
        provider.get_market_data("crypto_spot", "BTCUSDT", "1d")
    )

    assert result.available is False
    assert result.issues == ["malformed_exchange_candle"]
