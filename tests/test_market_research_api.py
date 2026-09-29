from fastapi.testclient import TestClient

from backend.app import main as main_module
from backend.app.data.base import MarketDataResult


client = TestClient(main_module.app)


def rising_candles(count=500):
    rows = []
    for index in range(count):
        close = 100.0 + index
        rows.append({
            "timestamp": 1_000_000.0 + index * 86400,
            "open": close - 0.2,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": 100.0,
        })
    return rows


def test_market_research_uses_only_quality_passing_provider_data(monkeypatch):
    class Provider:
        async def get_market_data(self, market, symbol, horizon):
            if symbol == "BAD":
                return MarketDataResult(False, False, False, {}, "fake", ["stale"])
            return MarketDataResult(
                True, True, True,
                {"candles": rising_candles(), "as_of": 1_500_000_000.0},
                "fake", [],
            )

    monkeypatch.setattr(main_module, "crypto_spot_provider", Provider())
    response = client.post("/v1/research/market", json={
        "market": "crypto_spot",
        "symbols": ["GOOD", "BAD"],
        "horizon": "1d",
        "initial_train_bars": 300,
        "test_bars": 80,
        "simulations": 100,
    })
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "REPORT_CREATED"
    assert body["accepted_dataset_count"] == 1
    assert "BAD:1d" in body["rejected"]
    assert body["report"]["pooled_assets_or_timeframes"] is False


def test_market_research_rejects_insufficient_history_without_failing_request(monkeypatch):
    class Provider:
        async def get_market_data(self, market, symbol, horizon):
            return MarketDataResult(
                True, True, True,
                {"candles": rising_candles(350)},
                "fake", [],
            )

    monkeypatch.setattr(main_module, "crypto_spot_provider", Provider())
    response = client.post("/v1/research/market", json={
        "market": "crypto_spot",
        "symbols": ["SHORT_HISTORY"],
        "horizon": "1d",
        "initial_train_bars": 300,
        "test_bars": 80,
        "simulations": 100,
    })
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "NO_QUALITY_PASSING_DATASETS"
    rejected = body["rejected"]["SHORT_HISTORY:1d"]
    assert rejected["candle_count"] == 350
    assert rejected["minimum_required"] == 380
    assert "insufficient_history_for_requested_walk_forward" in rejected["issues"]



def test_market_research_rejects_each_failed_quality_flag(monkeypatch):
    class Provider:
        async def get_market_data(self, market, symbol, horizon):
            flags = {
                "UNAVAILABLE": (False, True, True),
                "STALE": (True, False, True),
                "INCOMPLETE": (True, True, False),
            }[symbol]
            return MarketDataResult(
                *flags,
                {"candles": rising_candles()},
                "quality_test",
                ["quality_flag_failed"],
            )

    monkeypatch.setattr(main_module, "crypto_spot_provider", Provider())
    response = client.post("/v1/research/market", json={
        "market": "crypto_spot",
        "symbols": ["UNAVAILABLE", "STALE", "INCOMPLETE"],
        "horizon": "1d",
        "initial_train_bars": 300,
        "test_bars": 80,
        "simulations": 100,
    })
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "NO_QUALITY_PASSING_DATASETS"
    assert body["accepted_dataset_count"] == 0
    assert set(body["rejected"]) == {
        "UNAVAILABLE:1d", "STALE:1d", "INCOMPLETE:1d"
    }
    assert all(
        item["issues"] == ["quality_flag_failed"]
        for item in body["rejected"].values()
    )


def test_market_research_revalidates_provider_candles_before_accepting(monkeypatch):
    class Provider:
        async def get_market_data(self, market, symbol, horizon):
            candles = rising_candles()
            candles[-1]["close"] = float("nan")
            return MarketDataResult(True, True, True, {"candles": candles}, "lying_provider", [])

    monkeypatch.setattr(main_module, "crypto_spot_provider", Provider())
    response = client.post("/v1/research/market", json={
        "market": "crypto_spot", "symbols": ["BROKEN"], "horizon": "1d",
        "initial_train_bars": 300, "test_bars": 80, "simulations": 100,
    })
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "NO_QUALITY_PASSING_DATASETS"
    rejected = body["rejected"]["BROKEN:1d"]
    assert rejected["issues"][0] == "provider_data_integrity_failed"
    assert "candle_499_contains_non_finite_or_non_numeric_values" in rejected["issues"]
