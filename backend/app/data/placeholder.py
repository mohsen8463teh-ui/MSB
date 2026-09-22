from .base import MarketDataProvider, MarketDataResult


class PlaceholderMarketDataProvider(MarketDataProvider):
    """
    Deliberately returns unavailable data.

    This prevents M.S.B from generating fake market signals
    before real market-data adapters are connected.
    """

    name = "placeholder"

    async def get_market_data(
        self,
        market: str | None,
        symbol: str | None,
        horizon: str | None,
    ) -> MarketDataResult:
        return MarketDataResult(
            available=False,
            fresh=False,
            complete=False,
            data={},
        )
