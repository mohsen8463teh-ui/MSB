import pytest

from backend.app.core.intent import resolve_intent
from backend.app.core.validator import validate_data_quality


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("برای یک روز یک سهم بده", "1d"),
        ("برای ۱ روز آینده", "1d"),
        ("برای سه روز آینده", "3d"),
        ("برای یک هفته", "1w"),
        ("برای سه ماه آینده", "3m"),
        ("برای ۶ ماه", "6m"),
        ("برای یک سال", "1y"),
        ("analyze for 12 months", "1y"),
        ("intraday setup", "intraday"),
        ("امروز چه خبر", "intraday"),
    ],
)
def test_resolve_supported_horizons(query, expected):
    result = resolve_intent(query)

    assert result["horizon"] == expected
    assert result["supported_horizon"] is True


def test_unknown_horizon_is_not_guessed():
    result = resolve_intent("یک سهم مناسب معرفی کن")

    assert result["horizon"] is None
    assert result["supported_horizon"] is False


def test_data_quality_requires_all_three_checks():
    result = validate_data_quality(
        {"available": True, "fresh": True, "complete": False}
    )

    assert result.available is False
    assert result.fresh is True
    assert result.complete is False
    assert result.issues == ["market_data_incomplete"]


def test_missing_data_fails_closed():
    result = validate_data_quality(None)

    assert result.available is False
    assert result.fresh is False
    assert result.complete is False
    assert "live_market_data_not_connected" in result.issues
