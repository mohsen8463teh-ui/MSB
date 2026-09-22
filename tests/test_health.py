from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["project"] == "MSB"


def test_no_fake_signal_without_data():
    response = client.post(
        "/v1/analyze",
        json={
            "query": "برای یک روز یک سهم بده"
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["decision"] == "NO_TRADE"
    assert body["data_quality"]["available"] is False
