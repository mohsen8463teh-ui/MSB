from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_position_size_api_returns_research_only_result():
    response = client.post("/v1/risk/position-size", json={
        "equity": 100000, "risk_fraction": 0.01, "entry": 100,
        "stop": 95, "available_cash": 100000,
    })
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "CALCULATED_RESEARCH_ONLY"
    assert body["order_authorized"] is False
    assert body["result"]["quantity"] == 200
    assert body["result"]["estimated_loss_at_stop"] == 1000


def test_position_size_api_rejects_short_geometry_and_nonfinite():
    for payload in [
        {"equity": 100, "risk_fraction": .01, "entry": 10, "stop": 11, "available_cash": 100},
        {"equity": 100, "risk_fraction": .01, "entry": 10, "stop": 9, "available_cash": 100, "max_exposure_fraction": 2},
    ]:
        response = client.post("/v1/risk/position-size", json=payload)
        assert response.status_code == 422
