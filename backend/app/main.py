from fastapi import FastAPI

from .analysis.indicators import calculate_indicators
from .core.intent import resolve_intent
from .core.models import AnalyzeRequest, AnalysisResponse
from .core.protocol import PROTOCOL_VERSION
from .core.validator import validate_data_quality
from .data.crypto_spot import FallbackCryptoSpotMarketDataProvider
from .data.placeholder import PlaceholderMarketDataProvider
from .data.tsetmc_equity import TsetmcEquityMarketDataProvider


app = FastAPI(
    title="M.S.B",
    version=PROTOCOL_VERSION,
    description="Market Strategy Brain",
)

placeholder_provider = PlaceholderMarketDataProvider()
crypto_spot_provider = FallbackCryptoSpotMarketDataProvider()
iran_equity_provider = TsetmcEquityMarketDataProvider()


def get_data_provider(market: str | None):
    if market == "crypto_spot":
        return crypto_spot_provider
    if market == "iran_equity":
        return iran_equity_provider
    return placeholder_provider


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "project": "MSB",
        "protocol_version": PROTOCOL_VERSION,
    }


@app.post("/v1/analyze", response_model=AnalysisResponse)
async def analyze(request: AnalyzeRequest):
    intent = resolve_intent(request.query)
    horizon = request.horizon or intent["horizon"]
    provider = get_data_provider(request.market)

    market_data = await provider.get_market_data(
        market=request.market,
        symbol=request.symbol,
        horizon=horizon,
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
        except (KeyError, TypeError, ValueError) as error:
            quality.available = False
            quality.issues.append("analysis_input_invalid")
            reasoning.append(f"Indicator calculation was skipped: {error}.")
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
