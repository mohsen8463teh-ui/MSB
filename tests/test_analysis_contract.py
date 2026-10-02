from backend.app.core.models import AnalysisResponse, DataQuality


def test_analysis_response_exposes_explicit_abstention_and_evidence_fields():
    response = AnalysisResponse(
        protocol_version="1",
        decision="NO_TRADE",
        market="iran_equity",
        horizon="1w",
        data_quality=DataQuality(),
        evidence=["price above SMA20"],
        counter_evidence=["volume confirmation missing"],
        uncertainty=["strategy not validated"],
        no_trade_reason="NO_VALIDATED_STRATEGY",
    )

    payload = response.model_dump()
    assert payload["decision"] == "NO_TRADE"
    assert payload["evidence"] == ["price above SMA20"]
    assert payload["counter_evidence"] == ["volume confirmation missing"]
    assert payload["uncertainty"] == ["strategy not validated"]
    assert payload["no_trade_reason"] == "NO_VALIDATED_STRATEGY"


def test_legacy_analysis_response_gets_safe_empty_defaults():
    response = AnalysisResponse(
        protocol_version="1",
        decision="NO_TRADE",
        data_quality=DataQuality(),
    )

    assert response.counter_evidence == []
    assert response.uncertainty == []
    assert response.no_trade_reason is None
