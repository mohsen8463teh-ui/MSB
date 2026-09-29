import pytest

from backend.app.core.journal import create_journal_record


def test_creates_no_trade_fixture_record():
    record = create_journal_record(
        market="crypto_spot", symbol="btc-usdt", horizon="1w",
        direction="FLAT", source_type="FIXTURE",
        evidence=["TEST: deterministic fixture"],
    )
    assert record["symbol"] == "BTC-USDT"
    assert record["decision"] == "NO_TRADE"
    assert record["source_type"] == "FIXTURE"
    assert record["data_as_of"] is None
    assert record["outcome"] is None
    assert record["journal_id"]


@pytest.mark.parametrize("kwargs", [
    {"market": "crypto_futures"},
    {"symbol": ""},
    {"direction": "SHORT"},
    {"decision": "BUY"},
    {"source_type": "UNKNOWN"},
    {"source_type": "TEST", "data_as_of": "2026-01-01T00:00:00Z"},
    {"direction": "LONG", "entry": 10, "stop": 10},
    {"direction": "LONG", "entry": 10, "stop": 11},
    {"entry": True},
])
def test_rejects_invalid_or_unsafe_record(kwargs):
    base = dict(
        market="iran_equity", symbol="TEST", horizon="1d",
        direction="FLAT", source_type="TEST",
    )
    base.update(kwargs)
    with pytest.raises(ValueError):
        create_journal_record(**base)


def test_long_record_requires_stop_below_entry():
    record = create_journal_record(
        market="crypto_spot", symbol="ETH-USDT", horizon="1m",
        direction="LONG", source_type="HISTORICAL",
        entry=100, stop=95, targets=[105, 110],
    )
    assert record["entry"] == 100
    assert record["stop"] == 95
    assert record["targets"] == [105, 110]
