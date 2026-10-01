import asyncio
import json

import httpx
import pytest

from backend.app.analysis.tsetmc_scanner import TsetmcMarketScanner
from backend.app.data.base import MarketDataResult


def candles(count=220):
    rows = []
    for i in range(count):
        close = 100 + i * 0.2
        rows.append({"timestamp": 1_700_000_000 + i * 86400, "open": close,
                     "high": close + 1, "low": close - 1, "close": close, "volume": 100 + i})
    return rows


class FakeProvider:
    name = "fake_tsetmc"
    base_urls = ("https://mock.tsetmc.test/api",)

    async def get_market_data(self, market, symbol, horizon):
        if symbol == "خراب":
            return MarketDataResult(False, False, False, {}, self.name, ["not_fresh"])
        data = candles()
        return MarketDataResult(True, True, True,
                                {"candles": data, "as_of": data[-1]["timestamp"]},
                                self.name, [])


def test_scanner_marks_limited_universe_as_partial():
    async def run():
        scanner = TsetmcMarketScanner(provider=FakeProvider())
        async def universe():
            return ([{"symbol": f"نماد{i}"} for i in range(3)], [])
        scanner._universe = universe
        result = await scanner.scan(limit=2, concurrency=2)
        assert result["status"] == "PARTIAL_SCAN"
        assert result["coverage"] == {"universe_count": 3, "selected_count": 2,
                                      "scanned_count": 2, "coverage_fraction": 0.6667,
                                      "is_complete": False}
        assert result["candidate_count"] == 2
        assert all(x["decision"] == "NO_TRADE" and x["score_is_signal"] is False
                   for x in result["candidates"])
    asyncio.run(run())


def test_scanner_reports_rejected_symbols_and_error_details():
    async def run():
        scanner = TsetmcMarketScanner(provider=FakeProvider())
        async def universe():
            return ([{"symbol": "خراب"}], [])
        scanner._universe = universe
        result = await scanner.scan(limit=1)
        assert result["status"] == "NO_QUALITY_PASSING_CANDIDATES"
        assert result["scanned_count"] == 1
        assert result["rejected"][0]["issues"] == ["not_fresh"]
    asyncio.run(run())


def test_market_watch_parses_realistic_payload_and_keeps_instrument_id():
    async def run():
        def handler(request):
            assert request.url.path.endswith("/ClosingPrice/GetMarketWatch")
            return httpx.Response(200, json={"marketwatch": [
                {"lVal18AFC": "نماد", "insCode": 12345678},
                {"lVal18AFC": "نماد", "insCode": 12345678},
                {"lVal18AFC": "نماد۲", "insCode": "87654321"},
                {"lVal18AFC": ""},
                None,
            ]})
        scanner = TsetmcMarketScanner(provider=FakeProvider(),
                                      transport=httpx.MockTransport(handler))
        symbols, issues = await scanner._universe()
        assert symbols == [{"symbol": "نماد", "instrument_id": "12345678"},
                           {"symbol": "نماد۲", "instrument_id": "87654321"}]
        assert issues == ["market_watch_unresolved_rows:2"]
    asyncio.run(run())


@pytest.mark.parametrize("payload", [[], {"marketwatch": {}}, {"wrong": []}])
def test_market_watch_rejects_invalid_payload(payload):
    async def run():
        scanner = TsetmcMarketScanner(
            provider=FakeProvider(),
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload)))
        with pytest.raises(ValueError):
            await scanner._universe()
    asyncio.run(run())


def test_market_watch_rejects_non_json_response():
    async def run():
        scanner = TsetmcMarketScanner(
            provider=FakeProvider(),
            transport=httpx.MockTransport(lambda request: httpx.Response(200, text="<html>")))
        with pytest.raises(ValueError, match="invalid_tsetmc_market_watch_json"):
            await scanner._universe()
    asyncio.run(run())


def test_scanner_rejects_invalid_limits():
    async def run():
        scanner = TsetmcMarketScanner(provider=FakeProvider())
        with pytest.raises(ValueError):
            await scanner.scan(limit=0)
    asyncio.run(run())
