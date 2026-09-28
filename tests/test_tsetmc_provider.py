import asyncio
from datetime import date, datetime, timedelta
from urllib.parse import unquote
from zoneinfo import ZoneInfo

import httpx

from backend.app.data.tsetmc_equity import TsetmcEquityMarketDataProvider


TEHRAN = ZoneInfo("Asia/Tehran")
NOW = datetime(2025, 1, 3, 12, 0, tzinfo=TEHRAN).timestamp()


def history_rows():
    end = date(2025, 1, 2)
    rows = []
    for index in range(220):
        day = end - timedelta(days=index)
        close = 100.0 + index
        rows.append(
            {
                "dEven": int(day.strftime("%Y%m%d")),
                "priceFirst": close - 0.2,
                "priceMax": close + 0.5,
                "priceMin": close - 0.5,
                "pClosing": close,
                "qTotTran5J": 1000,
            }
        )
    rows.insert(
        0,
        {
            "dEven": 20250103,
            "priceFirst": 1000,
            "priceMax": 1010,
            "priceMin": 990,
            "pClosing": 1005,
            "qTotTran5J": 500,
        },
    )
    return rows


def test_tsetmc_provider_resolves_exact_symbol_and_excludes_today():
    def handler(request):
        path = unquote(request.url.path)
        assert request.headers["user-agent"].startswith("Mozilla/")
        if path.endswith("/Instrument/GetInstrumentSearch/فملی"):
            return httpx.Response(
                200,
                json={
                    "instrumentSearch": [
                        {"insCode": "12345678901234567", "lVal18AFC": "فملی"}
                    ]
                },
            )
        if path.endswith(
            "/ClosingPrice/GetClosingPriceDailyList/12345678901234567/500"
        ):
            return httpx.Response(200, json={"closingPriceDaily": history_rows()})
        raise AssertionError(f"Unexpected URL: {request.url}")

    provider = TsetmcEquityMarketDataProvider(
        transport=httpx.MockTransport(handler),
        clock=lambda: NOW,
    )
    result = asyncio.run(
        provider.get_market_data("iran_equity", "فملی", "1d")
    )

    assert result.available is True
    assert result.fresh is True
    assert result.complete is True
    assert len(result.data["candles"]) == 220
    assert result.data["symbol"] == "فملی"
    assert result.data["instrument_id"] == "12345678901234567"
    assert result.data["candles"][-1]["close"] == 100.0


def test_tsetmc_provider_rejects_non_exact_symbol_match():
    def handler(request):
        return httpx.Response(
            200,
            json={
                "instrumentSearch": [
                    {"insCode": "12345678901234567", "lVal18AFC": "فملیح"}
                ]
            },
        )

    provider = TsetmcEquityMarketDataProvider(
        transport=httpx.MockTransport(handler),
        clock=lambda: NOW,
    )
    result = asyncio.run(
        provider.get_market_data("iran_equity", "فملی", "1d")
    )

    assert result.available is False
    assert result.issues == ["instrument_not_found"]


def test_tsetmc_provider_reports_http_status():
    def handler(request):
        return httpx.Response(403)

    provider = TsetmcEquityMarketDataProvider(
        transport=httpx.MockTransport(handler),
        clock=lambda: NOW,
    )
    result = asyncio.run(
        provider.get_market_data("iran_equity", "فملی", "1d")
    )

    assert result.available is False
    assert result.issues == ["tsetmc_http_403"]


def test_tsetmc_provider_reports_network_error_type():
    def handler(request):
        raise httpx.ConnectError("connection unavailable")

    provider = TsetmcEquityMarketDataProvider(
        transport=httpx.MockTransport(handler),
        clock=lambda: NOW,
    )
    result = asyncio.run(
        provider.get_market_data("iran_equity", "فملی", "1d")
    )

    assert result.available is False
    assert result.issues == ["tsetmc_network_ConnectError"]


def test_tsetmc_provider_does_not_claim_intraday_from_daily_bars():
    provider = TsetmcEquityMarketDataProvider(clock=lambda: NOW)
    result = asyncio.run(
        provider.get_market_data("iran_equity", "فملی", "intraday")
    )

    assert result.available is False
    assert result.issues == ["unsupported_horizon_for_daily_data"]
