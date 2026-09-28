import asyncio
import json

from backend.app.data.binance_spot import BinanceSpotMarketDataProvider
from backend.app.data.tsetmc_equity import TsetmcEquityMarketDataProvider


async def main():
    checks = (
        (
            "binance_spot",
            BinanceSpotMarketDataProvider(),
            "crypto_spot",
            "BTCUSDT",
            "1d",
        ),
        (
            "tsetmc_equity",
            TsetmcEquityMarketDataProvider(),
            "iran_equity",
            "فملی",
            "1d",
        ),
    )
    report = []
    for name, provider, market, symbol, horizon in checks:
        result = await provider.get_market_data(market, symbol, horizon)
        report.append(
            {
                "provider": name,
                "available": result.available,
                "fresh": result.fresh,
                "complete": result.complete,
                "candle_count": len(result.data.get("candles", [])),
                "as_of": result.data.get("as_of"),
                "issues": result.issues,
            }
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
