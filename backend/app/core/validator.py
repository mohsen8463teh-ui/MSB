from .models import DataQuality


def validate_data_quality(data: dict | None) -> DataQuality:
    if not isinstance(data, dict):
        return DataQuality(
            available=False,
            fresh=False,
            complete=False,
            issues=["live_market_data_not_connected"],
        )

    issues = []
    flags = ("available", "fresh", "complete")
    normalized = {}
    for flag in flags:
        value = data.get(flag)
        normalized[flag] = value is True
        if not isinstance(value, bool):
            issues.append(f"market_data_invalid_{flag}_flag")
        elif value is False:
            issue = {
                "available": "market_data_unavailable",
                "fresh": "market_data_not_fresh",
                "complete": "market_data_incomplete",
            }[flag]
            issues.append(issue)

    return DataQuality(
        available=not issues,
        fresh=normalized["fresh"],
        complete=normalized["complete"],
        issues=issues,
    )
