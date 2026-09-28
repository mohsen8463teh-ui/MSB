from __future__ import annotations

import math
import re
import unicodedata
from datetime import datetime, time
from urllib.parse import quote
from zoneinfo import ZoneInfo

import httpx

from .base import MarketDataProvider, MarketDataResult
from .validation import validate_ohlcv


_TEHRAN = ZoneInfo("Asia/Tehran")
_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_SUPPORTED_DAILY_HORIZONS = {"1d", "3d", "1w", "1m", "3m", "5m", "6m", "1y"}


def _normalize_symbol(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip()
    return normalized.replace("ي", "ی").replace("ك", "ک").upper()


class TsetmcEquityMarketDataProvider(MarketDataProvider):
    """Read-only TSETMC daily candles with exact-symbol resolution."""

    name = "tsetmc_equity"
    BASE_URL = "https://cdn.tsetmc.com/api"

    def __init__(
        self,
        *,
        base_url: str = BASE_URL,
        timeout_seconds: float = 12.0,
        transport: httpx.AsyncBaseTransport | None = None,
        clock=None,
    ) -> None:
        import time as time_module

        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be a finite positive number")
        if not isinstance(base_url, str) or not base_url.startswith(("https://", "http://")):
            raise ValueError("base_url must be an HTTP(S) URL")
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = float(timeout_seconds)
        self.transport = transport
        self.clock = clock or time_module.time

    async def get_market_data(
        self,
        market: str | None,
        symbol: str | None,
        horizon: str | None,
    ) -> MarketDataResult:
        if market != "iran_equity":
            return self._unavailable("unsupported_market")
        if not symbol or len(symbol.strip()) > 32:
            return self._unavailable("invalid_or_missing_symbol")
        if horizon not in _SUPPORTED_DAILY_HORIZONS:
            return self._unavailable("unsupported_horizon_for_daily_data")

        try:
            raw_now = self.clock()
            if isinstance(raw_now, bool) or not isinstance(raw_now, (int, float)):
                return self._unavailable("invalid_provider_clock")
            now = float(raw_now)
            if not math.isfinite(now):
                return self._unavailable("invalid_provider_clock")
            today_tehran = datetime.fromtimestamp(now, _TEHRAN).date()
        except Exception:
            return self._unavailable("invalid_provider_clock")

        headers = {
            "User-Agent": _USER_AGENT,
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout_seconds,
                transport=self.transport,
                headers=headers,
            ) as client:
                search_path = (
                    "/Instrument/GetInstrumentSearch/"
                    + quote(symbol.strip(), safe="")
                )
                search_response = await client.get(search_path)
                search_response.raise_for_status()
                search_payload = search_response.json()
                if not isinstance(search_payload, dict):
                    return self._unavailable("invalid_instrument_search_payload")
                matches = search_payload.get("instrumentSearch")
                if not isinstance(matches, list):
                    return self._unavailable("invalid_instrument_search_payload")

                exact = [
                    item
                    for item in matches
                    if isinstance(item, dict)
                    and _normalize_symbol(str(item.get("lVal18AFC", "")))
                    == _normalize_symbol(symbol)
                ]
                if len(exact) == 0:
                    return self._unavailable("instrument_not_found")
                if len(exact) > 1:
                    return self._unavailable("ambiguous_instrument_symbol")

                instrument_id = str(exact[0].get("insCode", ""))
                if not re.fullmatch(r"\d{8,20}", instrument_id):
                    return self._unavailable("invalid_instrument_identifier")

                history_response = await client.get(
                    f"/ClosingPrice/GetClosingPriceDailyList/{instrument_id}/500"
                )
                history_response.raise_for_status()
                history_payload = history_response.json()
                if not isinstance(history_payload, dict):
                    return self._unavailable("invalid_daily_history_payload")
                rows = history_payload.get("closingPriceDaily")
                if not isinstance(rows, list):
                    return self._unavailable("invalid_daily_history_payload")

            candles = []
            for row in rows:
                if not isinstance(row, dict):
                    return self._unavailable("malformed_daily_history_row")
                try:
                    trading_date = datetime.strptime(
                        str(row.get("dEven")), "%Y%m%d"
                    ).date()
                except (TypeError, ValueError):
                    return self._unavailable("invalid_daily_history_date")

                if trading_date >= today_tehran:
                    continue

                timestamp = datetime.combine(
                    trading_date, time(12, 0), tzinfo=_TEHRAN
                ).timestamp()
                candles.append(
                    {
                        "timestamp": timestamp,
                        "open": row.get("priceFirst"),
                        "high": row.get("priceMax"),
                        "low": row.get("priceMin"),
                        "close": row.get("pClosing"),
                        "volume": row.get("qTotTran5J"),
                    }
                )

            candles.sort(key=lambda item: item["timestamp"])
            checked = validate_ohlcv(candles, now=now)
            if not checked["valid"] or not checked["candles"]:
                return MarketDataResult(
                    available=False,
                    fresh=False,
                    complete=False,
                    data={"candles": checked["candles"]},
                    source=self.name,
                    issues=checked["issues"] or ["invalid_daily_history"],
                )

            latest_timestamp = checked["candles"][-1]["timestamp"]
            age_seconds = now - latest_timestamp
            fresh = 0 <= age_seconds <= 5 * 24 * 60 * 60
            complete = len(checked["candles"]) >= 200
            issues = list(checked["issues"])
            if not fresh:
                issues.append("market_data_not_fresh")
            if not complete:
                issues.append("insufficient_history_for_indicators")

            return MarketDataResult(
                available=True,
                fresh=fresh,
                complete=complete,
                data={
                    "symbol": _normalize_symbol(symbol),
                    "instrument_id": instrument_id,
                    "candles": checked["candles"],
                    "as_of": latest_timestamp,
                },
                source=self.name,
                issues=issues,
            )
        except httpx.HTTPStatusError as error:
            return self._unavailable(f"tsetmc_http_{error.response.status_code}")
        except httpx.RequestError as error:
            return self._unavailable(
                f"tsetmc_network_{type(error).__name__}"
            )
        except (ValueError, TypeError, KeyError, AttributeError):
            return self._unavailable("invalid_tsetmc_response")

    def _unavailable(self, issue: str) -> MarketDataResult:
        return MarketDataResult(
            available=False,
            fresh=False,
            complete=False,
            data={},
            source=self.name,
            issues=[issue],
        )
