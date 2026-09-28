import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.analysis.indicators import calculate_indicators
from backend.app.data.binance_spot import BinanceSpotMarketDataProvider
from backend.app.data.crypto_spot import (
    FallbackCryptoSpotMarketDataProvider,
    OkxSpotMarketDataProvider,
)
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
            "okx_spot",
            OkxSpotMarketDataProvider(),
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

    fallback = FallbackCryptoSpotMarketDataProvider()
    result = await fallback.get_market_data("crypto_spot", "BTCUSDT", "1d")
    pipeline = {
        "provider": result.source,
        "data_ready": result.available and result.fresh and result.complete,
        "candle_count": len(result.data.get("candles", [])),
        "decision": "NO_TRADE",
        "indicators": None,
        "issues": result.issues,
    }
    if pipeline["data_ready"]:
        try:
            indicators = calculate_indicators(result.data.get("candles", []))
            pipeline["indicators"] = {
                "market_regime": indicators["market_regime"],
                "rsi14": indicators["rsi14"],
                "sma200": indicators["sma200"],
                "candles_used": indicators["candles_used"],
            }
        except (KeyError, TypeError, ValueError) as error:
            pipeline["issues"].append(
                "indicator_error_" + type(error).__name__
            )
    report.append({"pipeline": pipeline})
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
