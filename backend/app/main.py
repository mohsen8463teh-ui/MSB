from fastapi import FastAPI

from .core.intent import resolve_intent
from .core.models import AnalyzeRequest, AnalysisResponse
from .core.protocol import PROTOCOL_VERSION
from .core.validator import validate_data_quality
from .data.binance_spot import BinanceSpotMarketDataProvider
from .data.placeholder import PlaceholderMarketDataProvider


app = FastAPI(
    title="M.S.B",
    version=PROTOCOL_VERSION,
    description="Market Strategy Brain",
)

placeholder_provider = PlaceholderMarketDataProvider()
crypto_spot_provider = BinanceSpotMarketDataProvider()


def get_data_provider(market: str | None):
    if market == "crypto_spot":
        return crypto_spot_provider
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

    reasoning = [
        f"Data source: {market_data.source}.",
        "No validated analysis strategy is enabled yet.",
        "No fabricated signal is allowed.",
    ]
    if not quality.available:
        reasoning.insert(1, "Market data did not pass all quality checks.")
    else:
        reasoning.insert(1, "Market data passed the current integrity checks.")

    return AnalysisResponse(
        protocol_version=PROTOCOL_VERSION,
        decision="NO_TRADE",
        market=request.market,
        symbol=request.symbol.upper() if request.symbol else None,
        horizon=horizon,
        reasoning=reasoning,
        invalidation=[
            "An actionable signal requires a validated strategy and verified data."
        ],
        data_quality=quality,
    )
