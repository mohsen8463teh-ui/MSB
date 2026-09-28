from fastapi.testclient import TestClient

from backend.app import main as main_module
from backend.app.data.base import MarketDataResult


client = TestClient(main_module.app)


def valid_candles(count=220):
    rows = []
    for index in range(count):
        close = 100.0 + index
        rows.append(
            {
                "timestamp": 1_000_000.0 + index * 3600,
                "open": close - 0.2,
                "high": close + 0.5,
                "low": close - 0.5,
                "close": close,
                "volume": 10.0,
            }
        )
    return rows


class FakeCryptoProvider:
    name = "test_provider"

    async def get_market_data(self, market, symbol, horizon):
        return MarketDataResult(
            available=True,
            fresh=True,
            complete=True,
            data={"candles": valid_candles(), "as_of": 1_800_000_000.0},
            source=self.name,
        )


def test_crypto_market_data_and_indicators_never_create_actionable_signal(monkeypatch):
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
    assert body["indicators"]["candles_used"] == 220
    assert body["data_source"] == "test_provider"
    assert body["data_as_of"] == 1_800_000_000.0
    assert body["evidence"]
    assert "No validated trading strategy is enabled yet." in body["reasoning"]


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


def test_crypto_provider_exception_returns_safe_no_trade_response(monkeypatch):
    class RaisingProvider:
        name = "raising_provider"

        async def get_market_data(self, market, symbol, horizon):
            raise TimeoutError("upstream secret details")

    monkeypatch.setattr(main_module, "crypto_spot_provider", RaisingProvider())
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
    assert "provider_error" in body["data_quality"]["issues"]
    assert body["indicators"] is None
    assert "upstream secret details" not in response.text


def test_invalid_indicator_input_does_not_expose_exception_details(monkeypatch):
    class InvalidDataProvider:
        name = "invalid_provider"

        async def get_market_data(self, market, symbol, horizon):
            return MarketDataResult(
                available=True,
                fresh=True,
                complete=True,
                data={"candles": []},
                source=self.name,
            )

    monkeypatch.setattr(main_module, "crypto_spot_provider", InvalidDataProvider())
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
    assert "analysis_input_invalid" in body["data_quality"]["issues"]
    assert "provider data was invalid" in " ".join(body["reasoning"])
