from datetime import datetime, timezone

from fastapi.testclient import TestClient

from backend.app import main as main_module
from backend.app.data.base import MarketDataResult


def test_iran_equity_analyze_route_uses_tsetmc_provider_and_fails_closed(monkeypatch):
    now = datetime.now(timezone.utc).timestamp()
    candles = []
    for index in range(220):
        close = 100.0 + index
        candles.append({
            "timestamp": now - (220 - index) * 86400,
            "open": close - 0.2,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": 1000.0 + index,
        })

    class FakeTsetmcProvider:
        name = "tsetmc_equity"

        async def get_market_data(self, market, symbol, horizon):
            assert market == "iran_equity"
            assert symbol == "فملی"
            assert horizon == "1w"
            return MarketDataResult(
                available=True,
                fresh=True,
                complete=True,
                data={
                    "symbol": "فملی",
                    "instrument_id": "12345678901234567",
                    "candles": candles,
                    "as_of": candles[-1]["timestamp"],
                },
                source=self.name,
            )

    monkeypatch.setattr(main_module, "iran_equity_provider", FakeTsetmcProvider())
    with TestClient(main_module.app) as client:
        response = client.post("/v1/analyze", json={
            "query": "تحلیل فملی برای یک هفته",
            "market": "iran_equity",
            "symbol": "فملی",
            "horizon": "1w",
        })

    assert response.status_code == 200
    body = response.json()
    assert body["data_source"] == "tsetmc_equity"
    assert body["data_quality"]["available"] is True
    assert body["indicators"]["candles_used"] == 220
    # Live data availability must not be mistaken for a validated trade signal.
    assert body["decision"] == "NO_TRADE"
    assert "No validated trading strategy is enabled yet." in body["reasoning"]
