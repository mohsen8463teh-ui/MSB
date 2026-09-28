from fastapi.testclient import TestClient

from backend.app import main as main_module
from backend.app.data.base import MarketDataResult


client = TestClient(main_module.app)


class FakeCryptoProvider:
    name = "test_provider"

    async def get_market_data(self, market, symbol, horizon):
        return MarketDataResult(
            available=True,
            fresh=True,
            complete=True,
            data={"candles": [{"close": 100.0}]},
            source=self.name,
        )


def test_crypto_market_data_alone_never_creates_actionable_signal(monkeypatch):
    monkeypatch.setattr(
        main_module,
        "crypto_spot_provider",
        FakeCryptoProvider(),
    )

    response = client.post(
        "/v1/analyze",
        json={
            "query": "analyze BTC for one day",
            "market": "crypto_spot",
            "symbol": "BTCUSDT",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "NO_TRADE"
    assert body["data_quality"]["available"] is True
    assert "No validated analysis strategy is enabled yet." in body["reasoning"]


def test_crypto_provider_failure_is_reported_without_fake_signal(monkeypatch):
    class FailedProvider:
        name = "test_provider"

        async def get_market_data(self, market, symbol, horizon):
            return MarketDataResult(
                available=False,
                fresh=False,
                complete=False,
                data={},
                source=self.name,
                issues=["test_source_unavailable"],
            )

    monkeypatch.setattr(main_module, "crypto_spot_provider", FailedProvider())

    response = client.post(
        "/v1/analyze",
        json={
            "query": "analyze BTC for one day",
            "market": "crypto_spot",
            "symbol": "BTCUSDT",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "NO_TRADE"
    assert body["data_quality"]["available"] is False
    assert "test_source_unavailable" in body["data_quality"]["issues"]
