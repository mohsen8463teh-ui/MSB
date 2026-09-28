from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


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


def test_research_api_returns_separate_research_only_reports():
    response = client.post("/v1/research/report", json={
        "datasets": [
            {"dataset_id": "BTC:1d", "candles": rising_candles()},
            {"dataset_id": "ETH:1d", "candles": rising_candles()},
        ],
        "initial_train_bars": 300,
        "test_bars": 80,
        "simulations": 100,
    })
    assert response.status_code == 200
    body = response.json()
    assert body["research_only"] is True
    assert body["pooled_assets_or_timeframes"] is False
    assert set(body["reports"]) == {"BTC:1d", "ETH:1d"}


def test_research_api_rejects_duplicate_dataset_ids():
    candles = rising_candles()
    response = client.post("/v1/research/report", json={
        "datasets": [
            {"dataset_id": "BTC:1d", "candles": candles},
            {"dataset_id": "BTC:1d", "candles": candles},
        ],
        "initial_train_bars": 300,
        "test_bars": 80,
    })
    assert response.status_code == 422



def test_market_research_isolates_provider_errors_per_symbol(monkeypatch):
    class BrokenProvider:
        async def get_market_data(self, **kwargs):
            raise TimeoutError("private upstream details")

    import backend.app.main as main_module
    monkeypatch.setattr(main_module, "crypto_spot_provider", BrokenProvider())
    response = client.post("/v1/research/market", json={
        "market": "crypto_spot",
        "symbols": ["BTC"],
        "horizon": "1d",
        "initial_train_bars": 300,
        "test_bars": 80,
        "simulations": 100,
    })
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "NO_QUALITY_PASSING_DATASETS"
    rejection = body["rejected"]["BTC:1d"]
    assert rejection["issues"] == ["provider_error"]
    assert rejection["error_type"] == "TimeoutError"
    assert "private upstream details" not in response.text
