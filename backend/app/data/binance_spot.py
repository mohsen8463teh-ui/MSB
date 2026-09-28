from __future__ import annotations

import re
import time
from collections.abc import Callable
from typing import Any

import httpx

from .base import MarketDataProvider, MarketDataResult
from .validation import validate_ohlcv


class BinanceSpotMarketDataProvider(MarketDataProvider):
    """Read-only public Binance spot candles; never emits trade decisions."""

    name = "binance_spot"
    BASE_URL = "https://api.binance.com"
    HORIZON_CONFIG = {
        "intraday": ("15m", 200, 900),
        "1d": ("1h", 200, 3600),
        "3d": ("4h", 200, 14400),
        "1w": ("4h", 300, 14400),
        "1m": ("1d", 220, 86400),
        "3m": ("1d", 220, 86400),
        "5m": ("1d", 300, 86400),
        "6m": ("1d", 365, 86400),
        "1y": ("1d", 400, 86400),
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

    async def get_market_data(
        self,
        market: str | None,
        symbol: str | None,
        horizon: str | None,
    ) -> MarketDataResult:
        if market != "crypto_spot":
            return self._unavailable("unsupported_market")
        if not symbol or not re.fullmatch(r"[A-Za-z0-9]{3,20}", symbol):
            return self._unavailable("invalid_or_missing_symbol")
        if horizon not in self.HORIZON_CONFIG:
            return self._unavailable("unsupported_or_missing_horizon")

        interval, limit, interval_seconds = self.HORIZON_CONFIG[horizon]
        params = {"symbol": symbol.upper(), "interval": interval, "limit": limit}

        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.get("/api/v3/klines", params=params)
                response.raise_for_status()
                payload: Any = response.json()
            if not isinstance(payload, list):
                return self._unavailable("invalid_exchange_payload")

            now = self.clock()
            candles = []
            for row in payload:
                if not isinstance(row, list) or len(row) < 7:
                    return self._unavailable("malformed_exchange_candle")
                close_time = float(row[6]) / 1000.0
                if close_time >= now:
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
            fresh = bool(checked["candles"]) and latest_age <= interval_seconds * 2
            complete = checked["complete"]
            available = checked["valid"] and bool(checked["candles"])
            issues = list(checked["issues"])
            if not checked["candles"]:
                issues.append("no_closed_candles")
            if not fresh:
                issues.append("market_data_not_fresh")
            return MarketDataResult(
                available=available,
                fresh=fresh,
                complete=complete,
                data={
                    "symbol": symbol.upper(),
                    "interval": interval,
                    "candles": checked["candles"],
                    "as_of": checked["candles"][-1]["timestamp"]
                    if checked["candles"]
                    else None,
                },
                source=self.name,
                issues=issues,
            )
        except httpx.HTTPStatusError as error:
            return self._unavailable(f"exchange_http_{error.response.status_code}")
        except httpx.RequestError as error:
            return self._unavailable(
                f"exchange_network_{type(error).__name__}"
            )
        except (ValueError, TypeError, IndexError, KeyError):
            return self._unavailable("invalid_exchange_response")

    def _unavailable(self, issue: str) -> MarketDataResult:
        return MarketDataResult(
            available=False,
            fresh=False,
            complete=False,
            data={},
            source=self.name,
            issues=[issue],
        )
