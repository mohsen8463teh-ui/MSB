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



def probe_iran_equity_api():
    try:
        with TestClient(app) as client:
            response = client.post(
                "/v1/analyze",
                json={
                    "query": "analyze فملی for one week",
                    "market": "iran_equity",
                    "symbol": "فملی",
                    "horizon": "1w",
                },
            )
        if response.status_code != 200:
            return {"http_status": response.status_code, "api_ok": False}
        body = response.json()
        indicators = body.get("indicators") or {}
        quality = body.get("data_quality") or {}
        return {
            "http_status": response.status_code,
            "api_ok": True,
            "data_source": body.get("data_source"),
            "data_ready": quality.get("available"),
            "fresh": quality.get("fresh"),
            "complete": quality.get("complete"),
            "candles_used": indicators.get("candles_used", 0),
            "decision": body.get("decision"),
            "issues": quality.get("issues", []),
        }
    except Exception as error:
        return {"api_ok": False, "error_type": type(error).__name__}

async def probe_tsetmc_mirrors():
    # Test alternate TSETMC CDN hosts from the same runner that executes MSB.
    # This isolates host reachability before changing the production provider.
    import httpx
    from urllib.parse import quote

    report = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "Accept": "application/json,text/plain,*/*",
        "Referer": "https://www.tsetmc.com/",
        "Origin": "https://www.tsetmc.com",
    }
    for host in ("https://cdn.tsetmc.com/api", "https://cdn10.tsetmc.com/api"):
        item = {
            "host": host,
            "search_ok": False,
            "history_ok": False,
            "market_watch_http_ok": False,
            "market_watch_payload_ok": False,
            "market_watch_has_rows": False,
            "candle_count": 0,
            "market_watch_rows": 0,
        }
        try:
            async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
                # Probe live market watch separately; daily history is not live data.
                market_watch_url = (
                    host + "/ClosingPrice/GetMarketWatch"
                    "?market=0&industrialGroup="
                    "&paperTypes%5B0%5D=1&paperTypes%5B1%5D=2"
                    "&paperTypes%5B2%5D=3&paperTypes%5B3%5D=4"
                    "&paperTypes%5B4%5D=5&paperTypes%5B5%5D=6"
                    "&paperTypes%5B6%5D=7&paperTypes%5B7%5D=8"
                    "&paperTypes%5B8%5D=9&showTraded=false"
                    "&withBestLimits=false&hEven=0&RefID=0"
                )
                watch_response = await client.get(market_watch_url)
                item["market_watch_status"] = watch_response.status_code
                watch_response.raise_for_status()
                item["market_watch_http_ok"] = True
                watch_payload = watch_response.json()
                watch_rows = (
                    watch_payload.get("marketwatch")
                    if isinstance(watch_payload, dict) else None
                )
                if isinstance(watch_rows, list):
                    item["market_watch_payload_ok"] = True
                    item["market_watch_rows"] = len(watch_rows)
                    item["market_watch_has_rows"] = len(watch_rows) > 0
                    item["market_watch_sample_keys"] = (
                        sorted(watch_rows[0].keys())[:30]
                        if watch_rows and isinstance(watch_rows[0], dict) else []
                    )

                response = await client.get(
                    host + "/Instrument/GetInstrumentSearch/" + quote("فملی", safe="")
                )
                item["search_status"] = response.status_code
                response.raise_for_status()
                payload = response.json()
                matches = payload.get("instrumentSearch", []) if isinstance(payload, dict) else []
                exact = [row for row in matches if isinstance(row, dict) and str(row.get("lVal18AFC", "")).replace("ي", "ی").replace("ك", "ک") == "فملی"]
                item["search_ok"] = len(exact) == 1
                if item["search_ok"]:
                    ins_code = str(exact[0].get("insCode", ""))
                    history = await client.get(
                        host + f"/ClosingPrice/GetClosingPriceDailyList/{ins_code}/500"
                    )
                    item["history_status"] = history.status_code
                    history.raise_for_status()
                    history_payload = history.json()
                    rows = history_payload.get("closingPriceDaily", []) if isinstance(history_payload, dict) else []
                    item["history_ok"] = isinstance(rows, list) and len(rows) > 0
                    item["candle_count"] = len(rows) if isinstance(rows, list) else 0
        except Exception as error:
            item["error_type"] = type(error).__name__
        report.append(item)
    return report


async def main():
    report = await probe_providers()
    report.append({"api_pipeline_1y": probe_api()})
    report.append({"iran_equity_api_pipeline_1w": probe_iran_equity_api()})
    # Always run the TSETMC host reachability probe in CI. Previously this
    # diagnostic existed but was never called, hiding the actual network failure.
    report.append({"tsetmc_mirror_probe": await probe_tsetmc_mirrors()})
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    output_path = Path("artifacts/tsetmc-live-probe.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered + "\\n", encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
