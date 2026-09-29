import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from backend.app.backtest.holdout import evaluate_baseline_holdout
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
    )
    tsetmc_symbols = ("فملی", "فولاد", "شستا", "وبملت", "خودرو")
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
                split_index = int(len(candles) * 0.7)
                holdout = evaluate_baseline_holdout(
                    candles,
                    split_index=split_index,
                    initial_cash=100_000,
                    fee_bps=10,
                    slippage_bps=5,
                    max_exposure_fraction=0.95,
                )
                metrics = holdout["results"]
                item["fixed_holdout"] = {
                    "method": holdout["method"],
                    "research_only": True,
                    "training_period_used_for_parameter_fitting": False,
                    "train_bars": holdout["train_bars"],
                    "test_bars": holdout["test_bars"],
                    "test_start_utc": utc_time(holdout["test_start_timestamp"]),
                    "test_end_utc": utc_time(holdout["test_end_timestamp"]),
                    "closed_trades": metrics["closed_trades"],
                    "win_rate_pct": metrics["win_rate_pct"],
                    "realized_return_pct": metrics["realized_return_pct"],
                    "mark_to_market_return_pct": metrics["total_return_pct"],
                    "max_drawdown_pct": metrics["max_drawdown_pct"],
                    "open_position": metrics["open_position"] is not None,
                }
            except (KeyError, TypeError, ValueError) as error:
                item["fixed_holdout"] = {
                    "research_only": True,
                    "error_type": type(error).__name__,
                }
        report.append(item)
    # Probe several Iranian equities independently; one ticker is not
    # sufficient evidence that the live TSETMC path is healthy.
    tse_provider = TsetmcEquityMarketDataProvider()
    for symbol in tsetmc_symbols:
        result = await tse_provider.get_market_data("iran_equity", symbol, "1d")
        report.append({
            "provider": "tsetmc_equity",
            "symbol": symbol,
            "available": result.available,
            "fresh": result.fresh,
            "complete": result.complete,
            "candle_count": len(result.data.get("candles", [])),
            "as_of": result.data.get("as_of"),
            "issues": result.issues,
        })
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
