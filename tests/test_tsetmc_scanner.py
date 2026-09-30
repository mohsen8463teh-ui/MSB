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

    async def get_market_data(self, market, symbol, horizon):
        if symbol == "خراب":
            return MarketDataResult(False, False, False, {}, self.name, ["not_fresh"])
        return MarketDataResult(True, True, True,
                                {"candles": candles(), "as_of": candles()[-1]["timestamp"]},
                                self.name, [])


@pytest.mark.asyncio
async def test_scanner_ranks_only_quality_passed_symbols_and_never_emits_trade():
    scanner = TsetmcMarketScanner(provider=FakeProvider())
    async def universe():
        return ([{"symbol": "نماد۱"}, {"symbol": "خراب"}, {"symbol": "نماد۲"}], [])
    scanner._universe = universe
    result = await scanner.scan(horizon="1w", limit=10, concurrency=2)
    assert result["status"] == "SCAN_COMPLETED"
    assert result["scanned_count"] == 3
    assert result["candidate_count"] == 2
    assert len(result["rejected"]) == 1
    assert all(item["decision"] == "NO_TRADE" for item in result["candidates"])
    assert all(item["score_is_signal"] is False for item in result["candidates"])


@pytest.mark.asyncio
async def test_scanner_rejects_invalid_limits():
    scanner = TsetmcMarketScanner(provider=FakeProvider())
    with pytest.raises(ValueError):
        await scanner.scan(limit=0)
