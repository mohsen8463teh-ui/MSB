from __future__ import annotations

import re
import time
from collections.abc import Callable
from typing import Any

import httpx

from .base import MarketDataProvider, MarketDataResult
from .validation import validate_ohlcv


class OkxSpotMarketDataProvider(MarketDataProvider):
    """Read-only OKX public spot candles."""

    name = "okx_spot"
    BASE_URL = "https://www.okx.com"
    HORIZON_CONFIG = {
        "intraday": ("15m", 300, 900, 200),
        "1d": ("1H", 300, 3600, 200),
        "3d": ("4H", 300, 14400, 200),
        "1w": ("4H", 300, 14400, 200),
        "1m": ("1D", 300, 86400, 200),
        "3m": ("1D", 300, 86400, 200),
        "5m": ("1D", 300, 86400, 200),
        "6m": ("1D", 300, 86400, 200),
        "1y": ("1D", 100, 86400, 365),
    }

    def __init__(
        self,
        *,
        base_url: str = BASE_URL,
        timeout_seconds: float = 8.0,
        transport: httpx.AsyncBaseTransport | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.transport = transport
        self.clock = clock

    @staticmethod
    def _instrument_id(symbol: str) -> str | None:
        normalized = symbol.upper().replace("-", "").strip()
        if not re.fullmatch(r"[A-Z0-9]{6,20}", normalized):
            return None
        for quote in ("USDT", "USDC", "USD"):
            if normalized.endswith(quote) and len(normalized) > len(quote):
                return normalized[: -len(quote)] + "-" + quote
        return None

    @staticmethod
    def _validated_rows(payload: Any) -> list:
        if not isinstance(payload, dict) or payload.get("code") != "0":
            code = payload.get("code", "invalid") if isinstance(payload, dict) else "invalid"
            raise ValueError(f"okx_api_error_{code}")
        rows = payload.get("data")
        if not isinstance(rows, list):
            raise ValueError("invalid_okx_payload")
        return rows

    async def _fetch_1y_history(
        self,
        client: httpx.AsyncClient,
        inst_id: str,
        bar: str,
        target_count: int,
    ) -> list:
        rows_by_timestamp: dict[str, list] = {}
        after: str | None = None

        for _ in range(6):
            params = {"instId": inst_id, "bar": bar, "limit": "100"}
            if after is not None:
                params["after"] = after
            response = await client.get(
                "/api/v5/market/history-candles",
                params=params,
            )
            response.raise_for_status()
            rows = self._validated_rows(response.json())
            if not rows:
                break

            previous_count = len(rows_by_timestamp)
            for row in rows:
                if not isinstance(row, list) or len(row) < 9:
                    raise ValueError("malformed_okx_candle")
                rows_by_timestamp[str(row[0])] = row

            oldest = min(int(row[0]) for row in rows)
            after = str(oldest)
            if len(rows_by_timestamp) == previous_count:
                break
            if len(rows_by_timestamp) >= target_count:
                break

        return sorted(
            rows_by_timestamp.values(),
            key=lambda row: int(row[0]),
        )

    async def get_market_data(
        self,
        market: str | None,
        symbol: str | None,
        horizon: str | None,
    ) -> MarketDataResult:
        if market != "crypto_spot":
            return self._unavailable("unsupported_market")
        if not symbol:
            return self._unavailable("invalid_or_missing_symbol")
        inst_id = self._instrument_id(symbol)
        if inst_id is None:
            return self._unavailable("unsupported_symbol_format")
        if horizon not in self.HORIZON_CONFIG:
            return self._unavailable("unsupported_or_missing_horizon")

        bar, limit, interval_seconds, min_history = self.HORIZON_CONFIG[horizon]
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                if horizon == "1y":
                    rows = await self._fetch_1y_history(
                        client, inst_id, bar, min_history
                    )
                else:
                    response = await client.get(
                        "/api/v5/market/candles",
                        params={
                            "instId": inst_id,
                            "bar": bar,
                            "limit": str(limit),
                        },
                    )
                    response.raise_for_status()
                    rows = self._validated_rows(response.json())

            now = self.clock()
            candles = []
            for row in rows:
                if not isinstance(row, list) or len(row) < 9:
                    return self._unavailable("malformed_okx_candle")
                if str(row[8]) != "1":
                    continue
                candles.append(
                    {
                        "timestamp": float(row[0]) / 1000.0,
                        "open": row[1],
                        "high": row[2],
                        "low": row[3],
                        "close": row[4],
                        "volume": row[5],
                    }
                )
            candles.sort(key=lambda item: item["timestamp"])
            checked = validate_ohlcv(
                candles,
                interval_seconds=interval_seconds,
                now=now,
            )
            latest_age = (
                now - checked["candles"][-1]["timestamp"]
                if checked["candles"]
                else float("inf")
            )
            fresh = bool(checked["candles"]) and 0 <= latest_age <= interval_seconds * 2
            enough_history = len(checked["candles"]) >= min_history
            complete = checked["complete"] and enough_history
            available = checked["valid"] and bool(checked["candles"])
            issues = list(checked["issues"])
            if not candles:
                issues.append("no_closed_candles")
            if not fresh:
                issues.append("market_data_not_fresh")
            if not enough_history:
                issues.append("insufficient_history_for_horizon")
            return MarketDataResult(
                available=available,
                fresh=fresh,
                complete=complete,
                data={
                    "symbol": symbol.upper(),
                    "instrument_id": inst_id,
                    "interval": bar,
                    "candles": checked["candles"],
                    "as_of": checked["candles"][-1]["timestamp"]
                    if checked["candles"]
                    else None,
                },
                source=self.name,
                issues=issues,
            )
        except httpx.HTTPStatusError as error:
            return self._unavailable(f"okx_http_{error.response.status_code}")
        except httpx.RequestError as error:
            return self._unavailable(f"okx_network_{type(error).__name__}")
        except (ValueError, TypeError, IndexError, KeyError):
            return self._unavailable("invalid_okx_response")

    def _unavailable(self, issue: str) -> MarketDataResult:
        return MarketDataResult(
            available=False,
            fresh=False,
            complete=False,
            data={},
            source=self.name,
            issues=[issue],
        )


class FallbackCryptoSpotMarketDataProvider(MarketDataProvider):
    """Try Binance first, then OKX; return only fully quality-passing data."""

    name = "crypto_spot_fallback"

    def __init__(
        self,
        primary: MarketDataProvider | None = None,
        fallback: MarketDataProvider | None = None,
    ) -> None:
        from .binance_spot import BinanceSpotMarketDataProvider

        self.primary = primary or BinanceSpotMarketDataProvider()
        self.fallback = fallback or OkxSpotMarketDataProvider()

    async def get_market_data(
        self,
        market: str | None,
        symbol: str | None,
        horizon: str | None,
    ) -> MarketDataResult:
        primary_result = await self.primary.get_market_data(market, symbol, horizon)
        if (
            primary_result.available
            and primary_result.fresh
            and primary_result.complete
        ):
            return primary_result

        fallback_result = await self.fallback.get_market_data(
            market, symbol, horizon
        )
        if (
            fallback_result.available
            and fallback_result.fresh
            and fallback_result.complete
        ):
            return fallback_result

        return MarketDataResult(
            available=False,
            fresh=False,
            complete=False,
            data={},
            source=self.name,
            issues=[
                *(f"primary_{issue}" for issue in primary_result.issues),
                *(f"fallback_{issue}" for issue in fallback_result.issues),
            ],
        )
