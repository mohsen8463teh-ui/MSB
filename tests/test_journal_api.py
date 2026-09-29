from fastapi.testclient import TestClient

from backend.app import main
from backend.app.core.journal_store import JournalStore


def test_journal_api_create_list_get_and_reject_short(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "journal_store", JournalStore(tmp_path / "api.sqlite3"))
    client = TestClient(main.app)
    payload = {
        "market": "iran_equity", "symbol": "فولاد", "horizon": "1w",
        "direction": "LONG", "source_type": "TEST",
        "evidence": ["fixture evidence"], "entry": 100, "stop": 95,
        "targets": [105], "notes": "research only",
    }
    created = client.post("/v1/journal", json=payload)
    assert created.status_code == 201
    record = created.json()
    assert record["decision"] == "NO_TRADE"
    assert record["outcome"] is None
    assert record["data_as_of"] is None
    assert record["protocol_version"]

    listed = client.get("/v1/journal", params={"market": "iran_equity", "symbol": "فولاد"})
    assert listed.status_code == 200
    assert listed.json()["records"][0]["journal_id"] == record["journal_id"]
    fetched = client.get(f"/v1/journal/{record['journal_id']}")
    assert fetched.status_code == 200
    assert fetched.json() == record

    rejected = client.post("/v1/journal", json={**payload, "direction": "SHORT"})
    assert rejected.status_code == 422


def test_journal_api_rejects_fixture_live_timestamp(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "journal_store", JournalStore(tmp_path / "api.sqlite3"))
    client = TestClient(main.app)
    response = client.post("/v1/journal", json={
        "market": "crypto_spot", "symbol": "BTC-USDT", "horizon": "1d",
        "source_type": "FIXTURE", "data_as_of": "2026-09-29T00:00:00Z",
    })
    assert response.status_code == 422
