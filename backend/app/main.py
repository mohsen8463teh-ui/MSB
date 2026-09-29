from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .analysis.indicators import calculate_indicators
from .backtest.research_report import evaluate_research_universe
from .core.intent import resolve_intent
from .core.models import AnalyzeRequest, AnalysisResponse
from .core.protocol import PROTOCOL_VERSION
from .core.validator import validate_data_quality
from .data.base import MarketDataResult
from .data.crypto_spot import FallbackCryptoSpotMarketDataProvider
from .data.placeholder import PlaceholderMarketDataProvider
from .data.tsetmc_equity import TsetmcEquityMarketDataProvider
from .data.validation import validate_ohlcv


class ResearchDataset(BaseModel):
    dataset_id: str = Field(min_length=1, max_length=100)
    candles: list[dict[str, Any]] = Field(min_length=492, max_length=10000)


class MarketResearchRequest(BaseModel):
    market: str = Field(pattern="^(crypto_spot|iran_equity)$")
    symbols: list[str] = Field(min_length=1, max_length=10)
    horizon: str = Field(pattern="^(1d|3d|1w|1m|3m|5m|6m|1y)$")
    initial_train_bars: int = Field(default=400, ge=200, le=9000)
    test_bars: int = Field(default=90, ge=2, le=5000)
    simulations: int = Field(default=2000, ge=100, le=10000)
    seed: int = Field(default=7, ge=0, le=2147483647)


class ResearchReportRequest(BaseModel):
    datasets: list[ResearchDataset] = Field(min_length=1, max_length=10)
    initial_train_bars: int = Field(default=400, ge=200, le=9000)
    test_bars: int = Field(default=90, ge=2, le=5000)
    simulations: int = Field(default=2000, ge=100, le=10000)
    seed: int = Field(default=7, ge=0, le=2147483647)


app = FastAPI(
    title="M.S.B",
    version=PROTOCOL_VERSION,
    description="Market Strategy Brain",
)

placeholder_provider = PlaceholderMarketDataProvider()
crypto_spot_provider = FallbackCryptoSpotMarketDataProvider()
iran_equity_provider = TsetmcEquityMarketDataProvider()
FRONTEND_FILE = Path(__file__).resolve().parents[2] / "frontend" / "index.html"


def get_data_provider(market: str | None):
    if market == "crypto_spot":
        return crypto_spot_provider
    if market == "iran_equity":
        return iran_equity_provider
    return placeholder_provider


@app.get("/", include_in_schema=False)
async def dashboard():
    return FileResponse(FRONTEND_FILE, media_type="text/html")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "project": "MSB",
        "protocol_version": PROTOCOL_VERSION,
    }


@app.post("/v1/research/report")
async def research_report(request: ResearchReportRequest):
    """Run isolated walk-forward and bootstrap research on supplied OHLCV data.

    This endpoint never generates a live signal and never combines datasets.
    """
    ids = [item.dataset_id.strip() for item in request.datasets]
    if len(set(ids)) != len(ids):
        raise HTTPException(status_code=422, detail="dataset_id values must be unique")
    datasets = {item.dataset_id.strip(): item.candles for item in request.datasets}
    try:
        return evaluate_research_universe(
            datasets,
            initial_train_bars=request.initial_train_bars,
            test_bars=request.test_bars,
            simulations=request.simulations,
            seed=request.seed,
        )
    except (TypeError, ValueError, KeyError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/v1/research/market")
async def research_market(request: MarketResearchRequest):
    """Fetch provider history, then research only quality-passing datasets."""
    normalized = [symbol.strip() for symbol in request.symbols]
    if any(not symbol or len(symbol) > 32 for symbol in normalized):
        raise HTTPException(status_code=422, detail="invalid symbol")
    if len({symbol.upper() for symbol in normalized}) != len(normalized):
        raise HTTPException(status_code=422, detail="symbols must be unique")
    provider = get_data_provider(request.market)
    accepted: dict[str, list[dict[str, Any]]] = {}
    rejected: dict[str, dict[str, Any]] = {}
    for symbol in normalized:
        dataset_id = f"{symbol.upper()}:{request.horizon}"
        try:
            result = await provider.get_market_data(
                market=request.market, symbol=symbol, horizon=request.horizon
            )
        except Exception as error:
            # A single provider failure must not abort research for other symbols.
            # Keep the public response useful without leaking exception details.
            rejected[dataset_id] = {
                "available": False,
                "fresh": False,
                "complete": False,
                "issues": ["provider_error"],
                "error_type": type(error).__name__,
            }
            continue
        if not (result.available and result.fresh and result.complete):
            rejected[dataset_id] = {
                "source": result.source,
                "available": result.available,
                "fresh": result.fresh,
                "complete": result.complete,
                "issues": result.issues,
            }
            continue
        candles = result.data.get("candles")
        if not isinstance(candles, list):
            rejected[dataset_id] = {
                "source": result.source, "issues": ["missing_candles"]
            }
            continue
        checked = validate_ohlcv(candles)
        if not checked["valid"] or not checked["complete"]:
            rejected[dataset_id] = {
                "source": result.source,
                "available": result.available,
                "fresh": result.fresh,
                "complete": False,
                "issues": ["provider_data_integrity_failed", *checked["issues"]],
            }
            continue
        candles = checked["candles"]
        minimum_bars = request.initial_train_bars + request.test_bars
        if len(candles) < minimum_bars:
            rejected[dataset_id] = {
                "source": result.source,
                "available": result.available,
                "fresh": result.fresh,
                "complete": result.complete,
                "issues": ["insufficient_history_for_requested_walk_forward"],
                "candle_count": len(candles),
                "minimum_required": minimum_bars,
            }
            continue
        accepted[dataset_id] = candles
    if not accepted:
        return {
            "status": "NO_QUALITY_PASSING_DATASETS",
            "market": request.market,
            "horizon": request.horizon,
            "accepted_dataset_count": 0,
            "rejected": rejected,
            "research_only": True,
        }
    try:
        report = evaluate_research_universe(
            accepted,
            initial_train_bars=request.initial_train_bars,
            test_bars=request.test_bars,
            simulations=request.simulations,
            seed=request.seed,
        )
    except (TypeError, ValueError, KeyError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {
        "status": "REPORT_CREATED",
        "market": request.market,
        "horizon": request.horizon,
        "accepted_dataset_count": len(accepted),
        "rejected": rejected,
        "report": report,
    }


@app.post("/v1/analyze", response_model=AnalysisResponse)
async def analyze(request: AnalyzeRequest):
    intent = resolve_intent(request.query)
    horizon = request.horizon or intent["horizon"]
    provider = get_data_provider(request.market)

    try:
        market_data = await provider.get_market_data(
            market=request.market,
            symbol=request.symbol,
            horizon=horizon,
        )
    except Exception:
        # Provider outages must produce a safe, explicit no-trade response.
        market_data = MarketDataResult(
            available=False,
            fresh=False,
            complete=False,
            data={},
            source=getattr(provider, "name", "unknown"),
            issues=["provider_error"],
        )

    quality = validate_data_quality(
        {
            "available": market_data.available,
            "fresh": market_data.fresh,
            "complete": market_data.complete,
        }
    )
    if market_data.issues:
        quality.issues.extend(
            issue for issue in market_data.issues if issue not in quality.issues
        )

    indicators = None
    evidence: list[str] = []
    reasoning = [f"Data source: {market_data.source}."]

    if quality.available:
        try:
            indicators = calculate_indicators(market_data.data.get("candles", []))
            evidence = [
                f"Market regime: {indicators['market_regime']}.",
                f"Momentum state: {indicators['momentum_state']}.",
                f"RSI state: {indicators['rsi_state']}.",
                f"Volume state: {indicators['volume_state']}.",
                f"Price above SMA20: {indicators['price_above_sma20']}.",
                f"Price above SMA50: {indicators['price_above_sma50']}.",
                f"Price above SMA200: {indicators['price_above_sma200']}.",
                f"Bullish SMA alignment: {indicators['trend_alignment_bullish']}.",
                f"20-candle breakout: {indicators['breakout20']}.",
            ]
            reasoning.append("Market data passed integrity and freshness checks.")
        except (KeyError, TypeError, ValueError):
            quality.available = False
            quality.issues.append("analysis_input_invalid")
            reasoning.append("Indicator calculation was skipped because the provider data was invalid.")
    else:
        reasoning.append("Market data did not pass all quality checks.")

    reasoning.extend(
        [
            "No validated trading strategy is enabled yet.",
            "No fabricated signal is allowed.",
        ]
    )

    return AnalysisResponse(
        protocol_version=PROTOCOL_VERSION,
        decision="NO_TRADE",
        market=request.market,
        symbol=request.symbol.upper() if request.symbol else None,
        horizon=horizon,
        data_source=market_data.source,
        data_as_of=market_data.data.get("as_of"),
        indicators=indicators,
        evidence=evidence,
        reasoning=reasoning,
        invalidation=[
            "An actionable signal requires a validated strategy and verified data."
        ],
        data_quality=quality,
    )
