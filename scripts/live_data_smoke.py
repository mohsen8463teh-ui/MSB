import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from backend.app.analysis.strategy_baseline import generate_sma_trend_signals
from backend.app.backtest.engine import run_long_only_backtest
from backend.app.data.binance_spot import BinanceSpotMarketDataProvider
from backend.app.data.crypto_spot import OkxSpotMarketDataProvider
from backend.app.data.tsetmc_equity import TsetmcEquityMarketDataProvider
from backend.app.main import app


def utc_time(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()


async def probe_providers():
    checks = (
        (
            "binance_spot",
            BinanceSpotMarketDataProvider(),
            "crypto_spot",
            "BTCUSDT",
            "1d",
        ),
        (
            "okx_spot_1d",
            OkxSpotMarketDataProvider(),
            "crypto_spot",
            "BTCUSDT",
            "1d",
        ),
        (
            "okx_spot_1y",
            OkxSpotMarketDataProvider(),
            "crypto_spot",
            "BTCUSDT",
            "1y",
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
        item = {
            "provider": name,
            "available": result.available,
            "fresh": result.fresh,
            "complete": result.complete,
            "candle_count": len(result.data.get("candles", [])),
            "as_of": result.data.get("as_of"),
            "issues": result.issues,
        }
        if name == "okx_spot_1y" and result.available and result.fresh and result.complete:
            candles = result.data["candles"]
            try:
                signals = generate_sma_trend_signals(candles)
                backtest = run_long_only_backtest(
                    candles,
                    signals["entry_signals"],
                    signals["exit_signals"],
                    initial_cash=100_000,
                    fee_bps=10,
                    slippage_bps=5,
                    max_exposure_fraction=0.95,
                )
                item["research_backtest"] = {
                    "strategy_id": signals["strategy_id"],
                    "research_only": True,
                    "period_start_utc": utc_time(candles[0]["timestamp"]),
                    "period_end_utc": utc_time(candles[-1]["timestamp"]),
                    "closed_trades": backtest["closed_trades"],
                    "win_rate_pct": backtest["win_rate_pct"],
                    "total_return_pct": backtest["total_return_pct"],
                    "max_drawdown_pct": backtest["max_drawdown_pct"],
                    "fees_total": backtest["fees_total"],
                    "open_position": backtest["open_position"] is not None,
                }
            except (KeyError, TypeError, ValueError) as error:
                item["research_backtest"] = {
                    "research_only": True,
                    "error_type": type(error).__name__,
                }
        report.append(item)
    return report


def probe_api():
    try:
        with TestClient(app) as client:
            response = client.post(
                "/v1/analyze",
                json={
                    "query": "analyze BTC for one year",
                    "market": "crypto_spot",
                    "symbol": "BTCUSDT",
                    "horizon": "1y",
                },
            )
        if response.status_code != 200:
            return {
                "http_status": response.status_code,
                "api_ok": False,
            }
        body = response.json()
        return {
            "http_status": response.status_code,
            "api_ok": True,
            "data_source": body["data_source"],
            "data_ready": body["data_quality"]["available"],
            "decision": body["decision"],
            "market_regime": (
                body["indicators"]["market_regime"]
                if body["indicators"]
                else None
            ),
            "candles_used": (
                body["indicators"]["candles_used"]
                if body["indicators"]
                else 0
            ),
            "issues": body["data_quality"]["issues"],
        }
    except Exception as error:
        return {
            "api_ok": False,
            "error_type": type(error).__name__,
        }


async def main():
    report = await probe_providers()
    report.append({"api_pipeline_1y": probe_api()})
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
