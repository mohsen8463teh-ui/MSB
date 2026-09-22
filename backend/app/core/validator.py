from .models import DataQuality


def validate_data_quality(data: dict | None) -> DataQuality:
    if not data:
        return DataQuality(
            available=False,
            fresh=False,
            complete=False,
            issues=["live_market_data_not_connected"],
        )

    issues = []

    if not data.get("available", False):
        issues.append("market_data_unavailable")

    if not data.get("fresh", False):
        issues.append("market_data_not_fresh")

    if not data.get("complete", False):
        issues.append("market_data_incomplete")

    return DataQuality(
        available=len(issues) == 0,
        fresh=data.get("fresh", False),
        complete=data.get("complete", False),
        issues=issues,
    )
