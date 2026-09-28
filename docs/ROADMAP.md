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

- [x] TSETMC symbol search and daily-history adapter (mock-tested; live connectivity pending)
- [ ] Market watch / breadth
- [ ] Codal adapter
- [ ] Sector data
- [ ] News/events

### Crypto

- [x] Binance public spot OHLCV adapter (mock-tested; runner returned HTTP 451)
- [x] OKX public spot OHLCV adapter (live runner returned 399 completed daily bars for 1y)
- [x] Paginated one-year OKX history
- [x] Automatic Binance-to-OKX fallback
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

- [x] SMA20/50/200
- [x] Wilder RSI14 and ATR14
- [x] Momentum, volume ratio, support/resistance, breakout evidence
- [x] Descriptive market regime and evidence states (not a trade signal)
- [ ] Market structure
- [ ] Liquidity
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

- [x] Research-only long-only SMA baseline
- [ ] Validated spot/futures rules
- [ ] Entry, stop, targets, and risk/reward
- [ ] Invalidation and signal validity

## Phase 5 — Journal

- [ ] Signal ID and timestamp
- [ ] Market, symbol, direction, and horizon
- [ ] Entry, stop, and targets
- [ ] Data references and protocol/model versions
- [ ] Final outcome

## Phase 6 — Evaluation

- [x] Long-only next-open execution framework (not a strategy)
- [x] Fees, slippage, exposure cap, and open-position marking
- [x] Baseline strategy signal/backtest integration (synthetic tests only)
- [ ] Real-data walk-forward tests
- [ ] Out-of-sample testing
- [ ] Monte Carlo
- [ ] Drawdown
- [ ] Profit factor
- [ ] Average R
- [ ] Performance by market regime

## Phase 7 — User Interface

- [x] Local Persian RTL analysis dashboard (API-backed; no trade execution)
- [ ] Natural-language chat interface
