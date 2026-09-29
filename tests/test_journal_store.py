import pytest

from backend.app.core.journal import create_journal_record
from backend.app.core.journal_store import JournalStore


def record(symbol="BTC-USDT"):
    return create_journal_record(
        market="crypto_spot", symbol=symbol, horizon="1w",
        direction="FLAT", source_type="FIXTURE",
        evidence=["TEST: fixture only"],
    )


def test_journal_persists_and_filters(tmp_path):
    path = tmp_path / "journal.sqlite3"
    store = JournalStore(path)
    first = store.append(record())
    store.append(record("ETH-USDT"))

    reopened = JournalStore(path)
    assert reopened.get(first["journal_id"]) == first
    assert len(reopened.list_records(limit=10)) == 2
    assert [x["symbol"] for x in reopened.list_records(limit=10, symbol="eth-usdt")] == ["ETH-USDT"]


def test_store_rejects_non_no_trade():
    store = JournalStore(":memory:")
    with pytest.raises(ValueError):
        store.append({"decision": "BUY"})
