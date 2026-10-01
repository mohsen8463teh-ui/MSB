from __future__ import annotations

import asyncio
from typing import Any

import httpx

from .indicators import calculate_indicators
from ..data.tsetmc_equity import TsetmcEquityMarketDataProvider


class TsetmcMarketScanner:
    """Read-only TSETMC scan; descriptive ranking only, never a trade signal."""

    def __init__(self, provider=None, *, timeout_seconds: float = 20.0, transport=None):
        self.provider = provider or TsetmcEquityMarketDataProvider()
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    async def _universe(self) -> tuple[list[dict[str, Any]], list[str]]:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.tsetmc.com/",
            "Origin": "https://www.tsetmc.com",
        }
        url = self.provider.base_urls[0] + "/ClosingPrice/GetMarketWatch?market=0&industrialGroup=&paperTypes%5B0%5D=1&paperTypes%5B1%5D=2&paperTypes%5B2%5D=3&paperTypes%5B3%5D=4&paperTypes%5B4%5D=5&paperTypes%5B5%5D=6&paperTypes%5B6%5D=7&paperTypes%5B7%5D=8&paperTypes%5B8%5D=9&showTraded=false&withBestLimits=false&hEven=0&RefID=0"
        async with httpx.AsyncClient(timeout=self.timeout_seconds, headers=headers, follow_redirects=True, transport=self.transport) as client:
            response = await client.get(url)
            response.raise_for_status()
            try:
                payload = response.json()
            except ValueError as exc:
                raise ValueError("invalid_tsetmc_market_watch_json") from exc
        rows = payload.get("marketwatch") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            raise ValueError("invalid_tsetmc_market_watch_payload")
        symbols, seen, issues = [], set(), []
        malformed = 0
        for row in rows:
            if not isinstance(row, dict):
                malformed += 1
                continue
            symbol = next((row.get(k) for k in ("lVal18AFC", "symbol", "ticker", "lVal30") if isinstance(row.get(k), str) and row.get(k).strip()), None)
            if not symbol:
                malformed += 1
                continue
            key = symbol.replace("ي", "ی").replace("ك", "ک").strip()
            if key in seen:
                continue
            seen.add(key)
            raw_id = row.get("insCode")
            instrument_id = str(raw_id) if raw_id is not None and str(raw_id).isdigit() else None
            symbols.append({"symbol": key, "instrument_id": instrument_id})
        if malformed:
            issues.append(f"market_watch_unresolved_rows:{malformed}")
        if not symbols:
            raise ValueError("market_watch_contained_no_resolvable_symbols")
        return symbols, issues

    async def scan(self, *, horizon: str = "1w", limit: int = 120, concurrency: int = 4) -> dict[str, Any]:
        if horizon not in {"1d", "3d", "1w", "1m", "3m", "5m", "6m", "1y"}:
            raise ValueError("unsupported_horizon")
        if isinstance(limit, bool) or not 1 <= limit <= 6000:
            raise ValueError("limit_must_be_between_1_and_6000")
        if isinstance(concurrency, bool) or not 1 <= concurrency <= 12:
            raise ValueError("concurrency_must_be_between_1_and_12")
        universe, universe_issues = await self._universe()
        semaphore = asyncio.Semaphore(concurrency)
        accepted, rejected = [], []

        async def inspect(item):
            symbol = item["symbol"]
            async with semaphore:
                try:
                    # Preserve the exchange instrument identifier for providers that support it;
                    # current provider falls back to exact-symbol resolution.
                    by_id = getattr(self.provider, "get_market_data_by_instrument_id", None)
                    if item.get("instrument_id") and callable(by_id):
                        data = await by_id("iran_equity", item["instrument_id"], symbol, horizon)
                    else:
                        data = await self.provider.get_market_data("iran_equity", symbol, horizon)
                    if not (data.available and data.fresh and data.complete):
                        return None, {"symbol": symbol, "issues": data.issues or ["data_quality_gate_failed"]}
                    indicators = calculate_indicators(data.data.get("candles", []))
                    components = {
                        "trend": int(indicators["price_above_sma20"]) + int(indicators["price_above_sma50"]) + int(indicators["price_above_sma200"]),
                        "momentum": int(indicators["momentum20"] > 0) + int(indicators["momentum60"] > 0),
                        "volume": int((indicators["volume_ratio20"] or 0) >= 1.0),
                        "breakout": int(indicators["breakout20"]),
                    }
                    score = round(components["trend"] / 3 * 0.4 + components["momentum"] / 2 * 0.3 + components["volume"] * 0.15 + components["breakout"] * 0.15, 4)
                    return {"symbol": symbol, "instrument_id": item.get("instrument_id"), "score": score, "components": components, "indicators": indicators,
                            "data_as_of": data.data.get("as_of"), "source": data.source,
                            "decision": "NO_TRADE", "score_is_signal": False}, None
                except Exception as exc:
                    return None, {"symbol": symbol, "issues": ["scan_error"], "error_type": type(exc).__name__, "error": str(exc)[:240]}

        selected = universe[:limit]
        results = await asyncio.gather(*(inspect(item) for item in selected))
        for candidate, rejection in results:
            if candidate:
                accepted.append(candidate)
            elif rejection:
                rejected.append(rejection)
        accepted.sort(key=lambda x: (-x["score"], x["symbol"]))
        # Unresolved source rows mean the discovered universe may be incomplete.
        # Never label coverage complete when the source payload had omissions.
        partial = len(selected) < len(universe) or bool(universe_issues)
        status = "PARTIAL_SCAN" if partial else ("SCAN_COMPLETED" if accepted else "NO_QUALITY_PASSING_CANDIDATES")
        return {"status": status, "coverage": {"universe_count": len(universe), "selected_count": len(selected),
                "scanned_count": len(results), "coverage_fraction": round(len(results) / len(universe), 4) if universe else 0.0,
                "is_complete": not partial},
                "market": "iran_equity", "horizon": horizon, "universe_count": len(universe),
                "selected_count": len(selected), "scanned_count": len(results),
                "candidate_count": len(accepted), "candidates": accepted, "rejected": rejected,
                "universe_issues": universe_issues, "research_only": True,
                "notice": "Ranking is descriptive only; no validated strategy is enabled and no order is authorized."}
