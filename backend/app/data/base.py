from dataclasses import dataclass, field
from typing import Any


@dataclass
class MarketDataResult:
    available: bool
    fresh: bool
    complete: bool
    data: dict[str, Any]
    source: str = "unknown"
    issues: list[str] = field(default_factory=list)


class MarketDataProvider:
    name = "base"

    async def get_market_data(
        self,
        market: str | None,
        symbol: str | None,
        horizon: str | None,
    ) -> MarketDataResult:
        raise NotImplementedError
