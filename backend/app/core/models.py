from typing import Any, Literal

from pydantic import BaseModel, Field


Decision = Literal["BUY", "SELL", "WAIT", "NO_TRADE"]
Market = Literal["iran_equity", "crypto_spot", "crypto_futures"]
Horizon = Literal["intraday", "1d", "3d", "1w", "1m", "3m", "5m", "6m", "1y"]


class AnalyzeRequest(BaseModel):
    query: str = Field(min_length=1)
    symbol: str | None = None
    market: Market | None = None
    horizon: Horizon | None = None


class DataQuality(BaseModel):
    available: bool = False
    fresh: bool = False
    complete: bool = False
    issues: list[str] = Field(default_factory=list)


class AnalysisResponse(BaseModel):
    protocol_version: str
    decision: Decision
    market: str | None = None
    symbol: str | None = None
    horizon: str | None = None

    entry: Any | None = None
    stop: Any | None = None
    targets: list[Any] = Field(default_factory=list)

    risk_reward: Any | None = None
    reasoning: list[str] = Field(default_factory=list)
    invalidation: list[str] = Field(default_factory=list)

    data_quality: DataQuality
    signal_id: str | None = None
