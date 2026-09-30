"""Run this on the machine that will host MSB to diagnose TSETMC reachability."""
import asyncio
import json
import socket
import sys
from pathlib import Path
from urllib.parse import quote

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.data.tsetmc_equity import TsetmcEquityMarketDataProvider


SYMBOL = "فملی"
HOSTS = ("cdn.tsetmc.com", "cdn10.tsetmc.com", "webgw.tse.ir")


async def main():
    report = {"runtime": "local", "symbol": SYMBOL, "dns": {}, "https": {}, "provider": None}
    for host in HOSTS:
        try:
            report["dns"][host] = sorted({item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)})
        except OSError as error:
            report["dns"][host] = {"error": type(error).__name__}

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "Accept": "application/json,text/plain,*/*",
        "Referer": "https://www.tsetmc.com/",
        "Origin": "https://www.tsetmc.com",
    }
    urls = {
        "cdn_primary": "https://cdn.tsetmc.com/api/Instrument/GetInstrumentSearch/" + quote(SYMBOL, safe=""),
        "cdn_mirror": "https://cdn10.tsetmc.com/api/Instrument/GetInstrumentSearch/" + quote(SYMBOL, safe=""),
        "webgw_marketwatch": "https://webgw.tse.ir/InstrumentProvider/api/v1/MarketWatch/MarketWatchCash/fa",
        "webgw_tradingview": "https://webgw.tse.ir/InstrumentProvider/api/v1/TradingView/symbols?symbol=" + quote(SYMBOL, safe=""),
    }
    async with httpx.AsyncClient(timeout=12, headers=headers, follow_redirects=True) as client:
        for name, url in urls.items():
            try:
                response = await client.get(url)
                body = response.text[:240]
                try:
                    payload = response.json()
                    shape = sorted(payload.keys()) if isinstance(payload, dict) else type(payload).__name__
                except ValueError:
                    shape = "non_json"
                report["https"][name] = {
                    "status": response.status_code,
                    "final_host": response.url.host,
                    "content_type": response.headers.get("content-type"),
                    "payload_shape": shape,
                    "body_preview": body,
                }
            except httpx.RequestError as error:
                report["https"][name] = {"error": type(error).__name__, "message": str(error)[:240]}

    result = await TsetmcEquityMarketDataProvider().get_market_data("iran_equity", SYMBOL, "1d")
    report["provider"] = {
        "available": result.available,
        "fresh": result.fresh,
        "complete": result.complete,
        "source": result.source,
        "candles": len(result.data.get("candles", [])),
        "issues": result.issues,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
