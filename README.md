# M.S.B

## Market Strategy Brain

M.S.B is an AI-assisted market analysis platform for:

- Iran Stock Market
- Crypto Spot
- Crypto Futures

Supported analysis horizons:

- Intraday
- 1 day
- 3 days
- 1 week
- 1 month
- 3 months
- 5 months
- 6 months
- 1 year

## Core principle

M.S.B must behave as an analytical market assistant, not as a simple indicator scanner.

The system must:

1. Understand natural-language requests.
2. Resolve market, asset type and time horizon.
3. Gather current market data.
4. Evaluate market regime and structure.
5. Analyze multiple independent evidence groups.
6. Validate data quality.
7. Produce BUY / SELL / WAIT / NO_TRADE decisions when appropriate.
8. Never fabricate missing data.
9. Never claim guaranteed profit.
10. Never use future information in historical evaluation.
11. Journal every actionable signal.

## Markets

### Iran equities

- Price
- Volume
- Liquidity
- Market structure
- Trend
- Relative strength
- Buyer/seller pressure
- Sector
- Market regime
- Fundamental information
- Codal information
- TSETMC information
- Relevant news/events

### Crypto

- Price
- Volume
- Market structure
- Trend
- Volatility
- Liquidity
- Open Interest
- Funding
- Liquidations
- Basis
- Long/short positioning
- Spot flow/CVD when reliable
- BTC dominance
- On-chain information when reliable
- News/events
- Macro context

## Futures output

A valid futures signal may contain:

- Direction
- Entry zone
- Stop / invalidation
- TP1
- TP2
- TP3
- Risk/reward
- Suggested risk limits
- Signal validity
- Reasoning
- Invalidation conditions

## Spot output

A valid spot analysis may contain:

- BUY
- WAIT
- SELL

plus:

- Entry zone
- Targets
- Invalidation
- Horizon
- Reasoning

## Important

WAIT / NO_TRADE is a valid result.

If data quality is insufficient, M.S.B must not invent a signal.
