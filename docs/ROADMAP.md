# M.S.B Roadmap

## Phase 0 — Foundation

- [x] Project structure
- [x] Analysis protocol
- [x] Intent resolver
- [x] Data quality validation
- [x] No-fabrication behavior
- [x] API foundation
- [x] Strict OHLCV integrity contract

## Phase 1 — Market Data

### Iran

- [ ] TSETMC adapter
- [ ] Codal adapter
- [ ] Market breadth
- [ ] Sector data
- [ ] News/events

### Crypto

- [x] Binance public spot OHLCV adapter (mock-tested; live connectivity not yet verified)
- [ ] Additional exchange/fallback sources
- [ ] Futures
- [ ] Open Interest
- [ ] Funding
- [ ] Liquidations
- [ ] Basis
- [ ] Long/short positioning
- [ ] BTC dominance
- [ ] On-chain sources

## Phase 2 — Analysis Core

- [ ] Market regime
- [ ] Market structure
- [ ] Trend
- [ ] Momentum
- [ ] Liquidity
- [ ] Volatility
- [ ] Flow
- [ ] Fundamental context
- [ ] News/event context
- [ ] Cross-market context

## Phase 3 — AI Gateway

- [x] Basic natural-language horizon resolution
- [ ] Full market/asset intent resolution
- [ ] Structured market context
- [ ] AI analysis
- [ ] Evidence extraction
- [ ] Reasoning protocol
- [ ] Signal validation

## Phase 4 — Signal Engine

- [ ] Spot
- [ ] Futures
- [ ] Entry
- [ ] Stop
- [ ] Targets
- [ ] R:R
- [ ] Invalidation
- [ ] Signal validity

## Phase 5 — Journal

Every actionable signal must record:

- Signal ID
- Timestamp
- Market
- Symbol
- Direction
- Horizon
- Entry
- Stop
- Targets
- Data references
- Protocol version
- Model version
- Final outcome

## Phase 6 — Evaluation

- [ ] Walk-forward testing
- [ ] Out-of-sample testing
- [ ] Monte Carlo
- [ ] Drawdown
- [ ] Profit factor
- [ ] Average R
- [ ] Performance by market regime

## Phase 7 — User Interface

- [ ] Natural-language chat interface
