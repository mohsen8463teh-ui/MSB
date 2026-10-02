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



def test_tsetmc_provider_excludes_explicit_zero_volume_placeholder_rows():
    def handler(request):
        if "Instrument/GetInstrumentSearch" in request.url.path:
            return httpx.Response(200, json={"instrumentSearch": [
                {"insCode": "12345678901234567", "lVal18AFC": "فملی"}
            ]})
        rows = history_rows()
        rows.extend([
            {
                "dEven": 20241231,
                "priceFirst": 0,
                "priceMax": 0,
                "priceMin": 0,
                "pClosing": 2002,
                "qTotTran5J": 0,
            },
            {
                "dEven": 20241230,
                "priceFirst": 2100,
                "priceMax": 2000,
                "priceMin": 1900,
                "pClosing": 1950,
                "qTotTran5J": 0,
            },
        ])
        return httpx.Response(200, json={"closingPriceDaily": rows})

    provider = TsetmcEquityMarketDataProvider(
        transport=httpx.MockTransport(handler),
        clock=lambda: NOW,
    )
    result = asyncio.run(provider.get_market_data("iran_equity", "فملی", "1d"))

    assert result.available is True
    assert result.complete is True
    assert len(result.data["candles"]) == 220
    assert result.data["excluded_no_trade_rows"] == 2
    assert all(candle["open"] > 0 for candle in result.data["candles"])


def test_tsetmc_provider_still_rejects_zero_prices_when_volume_is_positive():
    def handler(request):
        if "Instrument/GetInstrumentSearch" in request.url.path:
            return httpx.Response(200, json={"instrumentSearch": [
                {"insCode": "12345678901234567", "lVal18AFC": "فملی"}
            ]})
        rows = history_rows()
        rows[1].update({
            "priceFirst": 0,
            "priceMax": 0,
            "priceMin": 0,
            "pClosing": 2002,
            "qTotTran5J": 100,
        })
        return httpx.Response(200, json={"closingPriceDaily": rows})

    provider = TsetmcEquityMarketDataProvider(
        transport=httpx.MockTransport(handler),
        clock=lambda: NOW,
    )
    result = asyncio.run(provider.get_market_data("iran_equity", "فملی", "1d"))

    assert result.available is False
    assert any("non_positive_price" in issue for issue in result.issues)


def test_tsetmc_provider_rejects_future_dated_history():
    def handler(request):
        if "Instrument/GetInstrumentSearch" in request.url.path:
            return httpx.Response(200, json={"instrumentSearch": [
                {"insCode": "12345678901234567", "lVal18AFC": "فملی"}
            ]})
        rows = history_rows()
        rows.append({
            "dEven": 20250104,
            "priceFirst": 1000,
            "priceMax": 1010,
            "priceMin": 990,
            "pClosing": 1005,
            "qTotTran5J": 500,
        })
        return httpx.Response(200, json={"closingPriceDaily": rows})

    provider = TsetmcEquityMarketDataProvider(
        transport=httpx.MockTransport(handler),
        clock=lambda: NOW,
    )
    result = asyncio.run(provider.get_market_data("iran_equity", "فملی", "1d"))
    assert result.available is False
    assert result.issues == ["future_daily_history_date"]


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


def test_tsetmc_provider_fails_closed_for_invalid_clock_values():
    for bad_clock in (True, False, float("nan"), float("inf"), "200"):
        provider = TsetmcEquityMarketDataProvider(clock=lambda value=bad_clock: value)
        result = asyncio.run(
            provider.get_market_data("iran_equity", "فملی", "1d")
        )
        assert result.available is False
        assert result.issues == ["invalid_provider_clock"]


def test_tsetmc_provider_fails_closed_when_clock_raises():
    def broken_clock():
        raise RuntimeError("clock unavailable")

    provider = TsetmcEquityMarketDataProvider(clock=broken_clock)
    try:
        result = asyncio.run(
            provider.get_market_data("iran_equity", "فملی", "1d")
        )
    except RuntimeError:
        raise AssertionError("provider leaked clock exception")

    assert result.available is False
    assert result.issues == ["invalid_provider_clock"]


import pytest


@pytest.mark.parametrize("bad_timeout", [0, -1, True, False, float("nan"), float("inf"), "12"])
def test_tsetmc_provider_rejects_invalid_timeout_configuration(bad_timeout):
    with pytest.raises(ValueError, match="finite positive number"):
        TsetmcEquityMarketDataProvider(timeout_seconds=bad_timeout)


@pytest.mark.parametrize("bad_base_url", ["", "ftp://example.com/api", None, 123])
def test_tsetmc_provider_rejects_invalid_base_url(bad_base_url):
    with pytest.raises(ValueError, match="HTTP.*URL"):
        TsetmcEquityMarketDataProvider(base_url=bad_base_url)


@pytest.mark.parametrize(
    ("search_json", "expected_issue"),
    [
        ([], "invalid_instrument_search_payload"),
        ({"instrumentSearch": {}}, "invalid_instrument_search_payload"),
    ],
)
def test_tsetmc_provider_rejects_malformed_search_payload(search_json, expected_issue):
    provider = TsetmcEquityMarketDataProvider(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=search_json)),
        clock=lambda: NOW,
    )
    result = asyncio.run(provider.get_market_data("iran_equity", "فملی", "1d"))
    assert result.available is False
    assert result.issues == [expected_issue]


@pytest.mark.parametrize(
    ("history_json", "expected_issue"),
    [
        ([], "invalid_daily_history_payload"),
        ({"closingPriceDaily": {}}, "invalid_daily_history_payload"),
        ({"closingPriceDaily": []}, "empty_daily_history"),
        ({"closingPriceDaily": [None]}, "malformed_daily_history_row"),
        ({"closingPriceDaily": [{"dEven": "not-a-date"}]}, "invalid_daily_history_date"),
    ],
)
def test_tsetmc_provider_rejects_malformed_history_payload(history_json, expected_issue):
    def handler(request):
        if "Instrument/GetInstrumentSearch" in request.url.path:
            return httpx.Response(200, json={"instrumentSearch": [
                {"insCode": "12345678901234567", "lVal18AFC": "فملی"}
            ]})
        return httpx.Response(200, json=history_json)

    provider = TsetmcEquityMarketDataProvider(
        transport=httpx.MockTransport(handler),
        clock=lambda: NOW,
    )
    result = asyncio.run(provider.get_market_data("iran_equity", "فملی", "1d"))
    assert result.available is False
    assert result.issues == [expected_issue]


def test_tsetmc_provider_does_not_mark_invalid_candle_fields_available():
    def handler(request):
        if "Instrument/GetInstrumentSearch" in request.url.path:
            return httpx.Response(200, json={"instrumentSearch": [
                {"insCode": "12345678901234567", "lVal18AFC": "فملی"}
            ]})
        rows = history_rows()
        rows[1]["pClosing"] = "not-a-price"
        return httpx.Response(200, json={"closingPriceDaily": rows})

    provider = TsetmcEquityMarketDataProvider(
        transport=httpx.MockTransport(handler),
        clock=lambda: NOW,
    )
    result = asyncio.run(provider.get_market_data("iran_equity", "فملی", "1d"))
    assert result.available is False
    assert any("non_finite_or_non_numeric" in issue for issue in result.issues)


def test_tsetmc_provider_fails_over_to_secondary_cdn_host():
    seen_hosts = []

    def handler(request):
        seen_hosts.append(request.url.host)
        if request.url.host == "cdn.tsetmc.com":
            raise httpx.ConnectError("primary host unreachable")
        path = unquote(request.url.path)
        if path.endswith("/Instrument/GetInstrumentSearch/فملی"):
            return httpx.Response(200, json={"instrumentSearch": [
                {"insCode": "12345678901234567", "lVal18AFC": "فملی"}
            ]})
        if path.endswith("/ClosingPrice/GetClosingPriceDailyList/12345678901234567/500"):
            return httpx.Response(200, json={"closingPriceDaily": history_rows()})
        raise AssertionError(f"Unexpected URL: {request.url}")

    provider = TsetmcEquityMarketDataProvider(
        transport=httpx.MockTransport(handler),
        clock=lambda: NOW,
    )
    result = asyncio.run(provider.get_market_data("iran_equity", "فملی", "1d"))

    assert result.available is True
    assert result.complete is True
    assert seen_hosts == [
        "cdn.tsetmc.com",
        "cdn10.tsetmc.com",
        "cdn10.tsetmc.com",
    ]



def test_tsetmc_provider_fails_over_when_primary_returns_non_json():
    seen_hosts = []

    def handler(request):
        seen_hosts.append(request.url.host)
        if request.url.host == "cdn.tsetmc.com":
            return httpx.Response(200, text="<html>temporary CDN error</html>")
        path = unquote(request.url.path)
        if path.endswith("/Instrument/GetInstrumentSearch/فملی"):
            return httpx.Response(200, json={"instrumentSearch": [
                {"insCode": "12345678901234567", "lVal18AFC": "فملی"}
            ]})
        if path.endswith("/ClosingPrice/GetClosingPriceDailyList/12345678901234567/500"):
            return httpx.Response(200, json={"closingPriceDaily": history_rows()})
        raise AssertionError(f"Unexpected URL: {request.url}")

    provider = TsetmcEquityMarketDataProvider(
        transport=httpx.MockTransport(handler),
        clock=lambda: NOW,
    )
    result = asyncio.run(provider.get_market_data("iran_equity", "فملی", "1d"))

    assert result.available is True
    assert result.complete is True
    assert seen_hosts == [
        "cdn.tsetmc.com",
        "cdn10.tsetmc.com",
        "cdn10.tsetmc.com",
    ]



def test_tsetmc_provider_fails_over_when_primary_search_shape_is_invalid():
    seen_hosts = []

    def handler(request):
        seen_hosts.append(request.url.host)
        if request.url.host == "cdn.tsetmc.com":
            return httpx.Response(200, json={"unexpected": []})
        path = unquote(request.url.path)
        if path.endswith("/Instrument/GetInstrumentSearch/فملی"):
            return httpx.Response(200, json={"instrumentSearch": [
                {"insCode": "12345678901234567", "lVal18AFC": "فملی"}
            ]})
        return httpx.Response(200, json={"closingPriceDaily": history_rows()})

    provider = TsetmcEquityMarketDataProvider(
        transport=httpx.MockTransport(handler),
        clock=lambda: NOW,
    )
    result = asyncio.run(provider.get_market_data("iran_equity", "فملی", "1d"))

    assert result.available is True
    assert seen_hosts == [
        "cdn.tsetmc.com",
        "cdn10.tsetmc.com",
        "cdn10.tsetmc.com",
    ]


def test_tsetmc_provider_fails_over_when_primary_history_shape_is_invalid():
    seen_hosts = []

    def handler(request):
        seen_hosts.append(request.url.host)
        path = unquote(request.url.path)
        if path.endswith("/Instrument/GetInstrumentSearch/فملی"):
            return httpx.Response(200, json={"instrumentSearch": [
                {"insCode": "12345678901234567", "lVal18AFC": "فملی"}
            ]})
        if request.url.host == "cdn.tsetmc.com":
            return httpx.Response(200, json={"unexpected": []})
        return httpx.Response(200, json={"closingPriceDaily": history_rows()})

    provider = TsetmcEquityMarketDataProvider(
        transport=httpx.MockTransport(handler),
        clock=lambda: NOW,
    )
    result = asyncio.run(provider.get_market_data("iran_equity", "فملی", "1d"))

    assert result.available is True
    assert seen_hosts == [
        "cdn.tsetmc.com",
        "cdn.tsetmc.com",
        "cdn10.tsetmc.com",
        "cdn10.tsetmc.com",
    ]


def test_tsetmc_provider_excludes_isolated_inconsistent_ohlc_row_without_repairing_prices():
    def handler(request):
        if "Instrument/GetInstrumentSearch" in request.url.path:
            return httpx.Response(200, json={"instrumentSearch": [
                {"insCode": "12345678901234567", "lVal18AFC": "فملی"}
            ]})
        rows = history_rows()
        # One traded source row has a high below its close; it must be excluded,
        # not silently corrected.
        rows[10].update({"priceMax": 1, "qTotTran5J": 1000})
        return httpx.Response(200, json={"closingPriceDaily": rows})

    provider = TsetmcEquityMarketDataProvider(
        transport=httpx.MockTransport(handler),
        clock=lambda: NOW,
    )
    result = asyncio.run(provider.get_market_data("iran_equity", "فملی", "1d"))

    assert result.available is True
    assert result.complete is True
    assert len(result.data["candles"]) == 219
    assert result.data["excluded_inconsistent_ohlc_rows"] == 1
    assert "excluded_inconsistent_ohlc_rows:1" in result.issues
    assert all(candle["high"] >= candle["close"] for candle in result.data["candles"])


def test_tsetmc_provider_fails_closed_when_inconsistent_ohlc_rows_exceed_tolerance():
    def handler(request):
        if "Instrument/GetInstrumentSearch" in request.url.path:
            return httpx.Response(200, json={"instrumentSearch": [
                {"insCode": "12345678901234567", "lVal18AFC": "فملی"}
            ]})
        rows = history_rows()
        for row in rows[1:12]:
            row.update({"priceMax": 1, "qTotTran5J": 1000})
        return httpx.Response(200, json={"closingPriceDaily": rows})

    provider = TsetmcEquityMarketDataProvider(
        transport=httpx.MockTransport(handler),
        clock=lambda: NOW,
    )
    result = asyncio.run(provider.get_market_data("iran_equity", "فملی", "1d"))

    assert result.available is False
    assert result.issues == [
        "too_many_inconsistent_daily_rows:excluded=11:traded_rows=220:allowed=1"
    ]
    assert result.data["quality"] == {
        "traded_rows": 220,
        "accepted_rows": 209,
        "excluded_inconsistent_ohlc_rows": 11,
        "allowed_inconsistent_ohlc_rows": 1,
        "excluded_no_trade_rows": 0,
    }


def test_tsetmc_provider_retries_all_history_when_500_rows_are_empty():
    seen_paths = []

    def handler(request):
        path = unquote(request.url.path)
        seen_paths.append(path)
        if "Instrument/GetInstrumentSearch" in path:
            return httpx.Response(200, json={"instrumentSearch": [
                {"insCode": "12345678901234567", "lVal18AFC": "فملی"}
            ]})
        if path.endswith("/ClosingPrice/GetClosingPriceDailyList/12345678901234567/500"):
            return httpx.Response(200, json={"closingPriceDaily": []})
        if path.endswith("/ClosingPrice/GetClosingPriceDailyList/12345678901234567/0"):
            return httpx.Response(200, json={"closingPriceDaily": history_rows()})
        raise AssertionError(f"Unexpected URL: {request.url}")

    provider = TsetmcEquityMarketDataProvider(
        transport=httpx.MockTransport(handler),
        clock=lambda: NOW,
        fallback_base_urls=(),
    )
    result = asyncio.run(provider.get_market_data("iran_equity", "فملی", "1d"))

    assert result.available is True
    assert result.complete is True
    assert len(result.data["candles"]) == 220
    assert seen_paths == [
        "/api/Instrument/GetInstrumentSearch/فملی",
        "/api/ClosingPrice/GetClosingPriceDailyList/12345678901234567/500",
        "/api/ClosingPrice/GetClosingPriceDailyList/12345678901234567/0",
    ]



def test_tsetmc_provider_uses_market_watch_instrument_id_without_symbol_search():
    requested = []

    def handler(request):
        path = unquote(request.url.path)
        requested.append(path)
        if path.endswith("/ClosingPrice/GetClosingPriceDailyList/98765432101234567/500"):
            return httpx.Response(200, json={"closingPriceDaily": history_rows()})
        raise AssertionError(f"Unexpected URL: {request.url}")

    provider = TsetmcEquityMarketDataProvider(
        transport=httpx.MockTransport(handler),
        clock=lambda: NOW,
        fallback_base_urls=(),
    )
    result = asyncio.run(
        provider.get_market_data_by_instrument_id(
            "iran_equity", "98765432101234567", "فملی", "1w"
        )
    )

    assert result.available is True
    assert result.data["instrument_id"] == "98765432101234567"
    assert result.data["symbol"] == "فملی"
    assert requested == [
        "/api/ClosingPrice/GetClosingPriceDailyList/98765432101234567/500"
    ]


@pytest.mark.parametrize("bad_id", [None, "", "123", "12345678x", "123456789012345678901", 12345678901234567])
def test_tsetmc_provider_rejects_invalid_market_watch_instrument_id(bad_id):
    provider = TsetmcEquityMarketDataProvider(clock=lambda: NOW)
    result = asyncio.run(
        provider.get_market_data_by_instrument_id(
            "iran_equity", bad_id, "فملی", "1w"
        )
    )
    assert result.available is False
    assert result.issues == ["invalid_instrument_identifier"]
