import re

from .protocol import SUPPORTED_HORIZONS


def resolve_intent(query: str) -> dict:
    q = query.lower().strip()

    horizon = None

    patterns = [
        (r"\b1\s*day\b|\bیک\s*روز\b|\bیکروزه\b", "1d"),
        (r"\b3\s*day\b|\bسه\s*روز\b", "3d"),
        (r"\b1\s*week\b|\bیک\s*هفته\b", "1w"),
        (r"\b1\s*month\b|\bیک\s*ماه\b", "1m"),
        (r"\b3\s*month\b|\bسه\s*ماه\b", "3m"),
        (r"\b5\s*month\b|\bپنج\s*ماه\b", "5m"),
        (r"\b6\s*month\b|\bشش\s*ماه\b", "6m"),
        (r"\b1\s*year\b|\bیک\s*سال\b", "1y"),
        (r"\bintraday\b|\bامروز\b|\bفوری\b", "intraday"),
    ]

    for pattern, value in patterns:
        if re.search(pattern, q):
            horizon = value
            break

    return {
        "query": query,
        "horizon": horizon,
        "raw": q,
        "supported_horizon": horizon in SUPPORTED_HORIZONS
        if horizon is not None
        else False,
    }
