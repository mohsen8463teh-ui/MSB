from __future__ import annotations

import math
import re
import unicodedata
from datetime import datetime, time, timezone, timedelta
from urllib.parse import quote
from zoneinfo import ZoneInfo

import httpx

from .base import MarketDataProvider, MarketDataResult
from .validation import validate_ohlcv


try:
    _TEHRAN = ZoneInfo("Asia/Tehran")
except Exception:
    # Iran has used UTC+03:30 year-round since 2023. Keep local diagnostics
    # usable on minimal Android/Python images without an OS tz database.
    _TEHRAN = timezone(timedelta(hours=3, minutes=30), name="Asia/Tehran")
_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_SUPPORTED_DAILY_HORIZONS = {"1d", "3d", "1w", "1m", "3m", "5m", "6m", "1y"}


def _normalize_symbol(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip()
    return normalized.replace("ي", "ی").replace("ك", "ک").upper()


def _is_zero_value(value) -> bool:
    if isinstance(value, bool):
        return False
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return False
    return math.isfinite(number) and number == 0


class TsetmcEquityMarketDataProvider(MarketDataProvider):
    """Read-only TSETMC daily candles with exact-symbol resolution."""

    name = "tsetmc_equity"
    BASE_URL = "https://cdn.tsetmc.com/api"

    def __init__(
        self,
        *,
        base_url: str = BASE_URL,
        fallback_base_urls: tuple[str, ...] = ("https://cdn10.tsetmc.com/api",),
        timeout_seconds: float = 12.0,
        transport: httpx.AsyncBaseTransport | None = None,
        clock=None,
    ) -> None:
        import time as time_module

        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be a finite positive number")
        if not isinstance(base_url, str) or not base_url.startswith(("https://", "http://")):
            raise ValueError("base_url must be an HTTP(S) URL")
        if not isinstance(fallback_base_urls, (tuple, list)) or any(
            not isinstance(url, str) or not url.startswith(("https://", "http://"))
            for url in fallback_base_urls
        ):
            raise ValueError("fallback_base_urls must contain HTTP(S) URLs")
        self.base_url = base_url.rstrip("/")
        self.base_urls = tuple(dict.fromkeys(
            [self.base_url, *(url.rstrip("/") for url in fallback_base_urls)]
        ))
        self.timeout_seconds = float(timeout_seconds)
        self.transport = transport
        self.clock = clock or time_module.time

    async def get_market_data(
        self,
        market: str | None,
        symbol: str | None,
        horizon: str | None,
        *,
        _instrument_id: str | None = None,
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
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.tsetmc.com/",
            "Origin": "https://www.tsetmc.com",
        }

        last_network_error = None
        last_http_error = None
        last_payload_error = None
        search_payload = None
        history_payload = None
        instrument_id = None
        for host in self.base_urls:
            try:
                async with httpx.AsyncClient(
                    base_url=host,
                    timeout=self.timeout_seconds,
                    transport=self.transport,
                    headers=headers,
                    follow_redirects=True,
                ) as client:
                    if _instrument_id is not None:
                        candidate_id = str(_instrument_id)
                        if not re.fullmatch(r"\d{8,20}", candidate_id):
                            return self._unavailable("invalid_instrument_identifier")
                        candidate_search = {"instrumentSearch": [{"insCode": candidate_id, "lVal18AFC": symbol}]}
                    else:
                        search_path = (
                            "/Instrument/GetInstrumentSearch/"
                            + quote(symbol.strip(), safe="")
                        )
                        search_response = await client.get(search_path)
                        search_response.raise_for_status()
                        candidate_search = search_response.json()
                        if not isinstance(candidate_search, dict):
                            last_payload_error = ValueError("invalid instrument search payload")
                            continue
                        matches = candidate_search.get("instrumentSearch")
                        if not isinstance(matches, list):
                            last_payload_error = ValueError("invalid instrument search payload")
                            continue
                        exact = [
                            item for item in matches
                            if isinstance(item, dict)
                            and _normalize_symbol(str(item.get("lVal18AFC", "")))
                            == _normalize_symbol(symbol)
                        ]
                        if len(exact) == 0:
                            return self._unavailable("instrument_not_found")
                        if len(exact) > 1:
                            return self._unavailable("ambiguous_instrument_symbol")
                        candidate_id = str(exact[0].get("insCode", ""))
                        if not re.fullmatch(r"\d{8,20}", candidate_id):
                            return self._unavailable("invalid_instrument_identifier")
                    history_response = await client.get(
                        f"/ClosingPrice/GetClosingPriceDailyList/{candidate_id}/500"
                    )
                    history_response.raise_for_status()
                    candidate_history = history_response.json()
                    if not isinstance(candidate_history, dict):
                        last_payload_error = ValueError("invalid daily history payload")
                        continue
                    if not isinstance(candidate_history.get("closingPriceDaily"), list):
                        last_payload_error = ValueError("invalid daily history payload")
                        continue
                    search_payload = candidate_search
                    history_payload = candidate_history
                    instrument_id = candidate_id
                    break
            except httpx.HTTPStatusError as error:
                last_http_error = error
                continue
            except httpx.RequestError as error:
                last_network_error = error
                continue
            except ValueError as error:
                # A CDN may return an HTML/error body with HTTP 200; try the mirror.
                last_payload_error = error
                continue

        if history_payload is None or instrument_id is None:
            if last_network_error is not None:
                return self._unavailable(f"tsetmc_network_{type(last_network_error).__name__}")
            if last_http_error is not None:
                return self._unavailable(f"tsetmc_http_{last_http_error.response.status_code}")
            if last_payload_error is not None:
                payload_issue = {
                    "invalid instrument search payload": "invalid_instrument_search_payload",
                    "invalid daily history payload": "invalid_daily_history_payload",
                }.get(str(last_payload_error), "invalid_tsetmc_json_payload")
                return self._unavailable(payload_issue)
            return self._unavailable("tsetmc_all_hosts_unavailable")
        rows = history_payload["closingPriceDaily"]
        candles = []
        excluded_no_trade_rows = 0
        excluded_inconsistent_ohlc_rows = 0
        for row in rows:
            if not isinstance(row, dict):
                return self._unavailable("malformed_daily_history_row")
            try:
                trading_date = datetime.strptime(str(row.get("dEven")), "%Y%m%d").date()
            except (TypeError, ValueError):
                return self._unavailable("invalid_daily_history_date")
            if trading_date > today_tehran:
                return self._unavailable("future_daily_history_date")
            if trading_date == today_tehran:
                continue
            # A zero-volume row is not a traded daily candle. TSETMC may
            # populate carried/stale closing or OHLC fields on halted and
            # no-trade days; including them can create false OHLC violations
            # or artificial returns. Keep the raw source untouched and omit
            # these rows from the analytical series.
            if _is_zero_value(row.get("qTotTran5J")):
                excluded_no_trade_rows += 1
                continue
            timestamp = datetime.combine(trading_date, time(12, 0), tzinfo=_TEHRAN).timestamp()
            candle = {
                "timestamp": timestamp,
                "open": row.get("priceFirst"),
                "high": row.get("priceMax"),
                "low": row.get("priceMin"),
                "close": row.get("pClosing"),
                "volume": row.get("qTotTran5J"),
            }
            # TSETMC occasionally publishes a traded row whose OHLC envelope
            # is internally inconsistent. Do not repair or synthesize prices:
            # isolate and exclude only this specific corrupt row. Other
            # validation failures (zero/non-numeric prices, bad timestamps,
            # etc.) remain fail-closed below.
            row_check = validate_ohlcv([candle], now=now)
            if row_check["issues"] == ["candle_0_inconsistent_ohlc"]:
                excluded_inconsistent_ohlc_rows += 1
                continue
            candles.append(candle)

        total_traded_rows = len(candles) + excluded_inconsistent_ohlc_rows
        tolerated_bad_rows = max(1, int(total_traded_rows * 0.005))
        if excluded_inconsistent_ohlc_rows > tolerated_bad_rows:
            return self._unavailable("too_many_inconsistent_daily_rows")

        candles.sort(key=lambda item: item["timestamp"])
        checked = validate_ohlcv(candles, now=now)
        if not checked["valid"] or not checked["candles"]:
            return MarketDataResult(
                available=False, fresh=False, complete=False,
                data={"candles": checked["candles"]}, source=self.name,
                issues=checked["issues"] or ["invalid_daily_history"],
            )
        latest_timestamp = checked["candles"][-1]["timestamp"]
        age_seconds = now - latest_timestamp
        fresh = 0 <= age_seconds <= 5 * 24 * 60 * 60
        complete = len(checked["candles"]) >= 200
        issues = list(checked["issues"])
        if excluded_inconsistent_ohlc_rows:
            issues.append(
                f"excluded_inconsistent_ohlc_rows:{excluded_inconsistent_ohlc_rows}"
            )
        if not fresh:
            issues.append("market_data_not_fresh")
        if not complete:
            issues.append("insufficient_history_for_indicators")
        return MarketDataResult(
            available=True, fresh=fresh, complete=complete,
            data={
                "symbol": _normalize_symbol(symbol),
                "instrument_id": instrument_id,
                "candles": checked["candles"],
                "as_of": latest_timestamp,
                "excluded_no_trade_rows": excluded_no_trade_rows,
                "excluded_inconsistent_ohlc_rows": excluded_inconsistent_ohlc_rows,
            },
            source=self.name, issues=issues,
        )

    async def get_market_data_by_instrument_id(
        self,
        market: str | None,
        instrument_id: str | None,
        symbol: str | None,
        horizon: str | None,
    ) -> MarketDataResult:
        """Fetch history directly by the market-watch instrument ID, without symbol search."""
        if not isinstance(instrument_id, str) or not re.fullmatch(r"\d{8,20}", instrument_id):
            return self._unavailable("invalid_instrument_identifier")
        return await self.get_market_data(
            market, symbol, horizon, _instrument_id=instrument_id
        )

    def _unavailable(self, issue: str) -> MarketDataResult:
        return MarketDataResult(
            available=False,
            fresh=False,
            complete=False,
            data={},
            source=self.name,
            issues=[issue],
        )
