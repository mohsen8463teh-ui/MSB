import re
import unicodedata

from .protocol import SUPPORTED_HORIZONS


_DIGIT_TRANSLATION = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
    "01234567890123456789",
)


def _normalize_query(query: str) -> str:
    """Normalize Persian/Arabic text and numerals without changing its meaning."""
    value = unicodedata.normalize("NFKC", query).translate(_DIGIT_TRANSLATION)
    value = value.replace("ي", "ی").replace("ك", "ک")
    value = value.replace("\u200c", " ")
    return re.sub(r"\s+", " ", value).strip().lower()


_HORIZON_PATTERNS = (
    (r"\b(?:intraday|intra\s*day)\b|امروز|فوری|درون\s*روزی", "intraday"),
    (r"\b(?:1\s*day|one\s*day|24\s*hours?)\b|(?:یک|1)\s*روز(?:ه)?", "1d"),
    (r"\b(?:3\s*days?|three\s*days?)\b|(?:سه|3)\s*روز(?:ه)?", "3d"),
    (r"\b(?:1\s*week|one\s*week)\b|یک\s*هفته(?:ای)?", "1w"),
    (r"\b(?:1\s*month|one\s*month)\b|(?:یک|1)\s*ماه(?:ه)?", "1m"),
    (r"\b(?:3\s*months?|three\s*months?)\b|(?:سه|3)\s*ماه(?:ه)?", "3m"),
    (r"\b(?:5\s*months?|five\s*months?)\b|(?:پنج|5)\s*ماه(?:ه)?", "5m"),
    (r"\b(?:6\s*months?|six\s*months?)\b|(?:شش|6)\s*ماه(?:ه)?", "6m"),
    (r"\b(?:1\s*year|one\s*year|12\s*months?)\b|یک\s*سال(?:ه)?", "1y"),
)


def resolve_intent(query: str) -> dict:
    """Resolve a supported analysis horizon from Persian or English text."""
    normalized = _normalize_query(query)
    horizon = None

    for pattern, value in _HORIZON_PATTERNS:
        if re.search(pattern, normalized):
            horizon = value
            break

    return {
        "query": query,
        "horizon": horizon,
        "raw": normalized,
        "supported_horizon": horizon in SUPPORTED_HORIZONS
        if horizon is not None
        else False,
    }
