from fastapi import FastAPI

from .core.intent import resolve_intent
from .core.models import AnalyzeRequest, AnalysisResponse
from .core.protocol import PROTOCOL_VERSION
from .core.validator import validate_data_quality
from .data.placeholder import PlaceholderMarketDataProvider


app = FastAPI(
    title="M.S.B",
    version=PROTOCOL_VERSION,
    description="Market Strategy Brain",
)

data_provider = PlaceholderMarketDataProvider()


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

    market_data = await data_provider.get_market_data(
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

    return AnalysisResponse(
        protocol_version=PROTOCOL_VERSION,
        decision="NO_TRADE",
        market=request.market,
        symbol=request.symbol,
        horizon=horizon,
        reasoning=[
            "M.S.B core is initialized.",
            "Live market data is not connected yet.",
            "No fabricated signal is allowed.",
        ],
        invalidation=[
            "A real signal requires verified live market data."
        ],
        data_quality=quality,
    )
