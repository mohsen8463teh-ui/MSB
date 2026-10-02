# M.S.B completion gates — evidence-based status

This document separates implemented infrastructure from a usable market-selection system.
A passing unit-test suite or a successful data request is not, by itself, evidence of a repeatable trading edge.

## Iran equities

### Implemented
- Read-only TSETMC exact-symbol search and daily-history adapter.
- OHLCV validation, stale/future-data rejection, and explicit handling of no-trade rows.
- Descriptive indicators and a research-only long-only SMA baseline.
- Next-open backtest mechanics with fees, slippage, exposure limits, and marked open positions.
- Fixed holdout and expanding-window walk-forward research functions.

### Blocking gates
- No market-wide instrument/universe discovery or market-watch breadth pipeline is wired into the API.
- `/v1/research/market` requires caller-supplied symbols and accepts at most 10; it is not a market scanner.
- The baseline has not passed sufficient real-data, multi-symbol out-of-sample evaluation. Existing documented holdout evidence includes zero closed trades.
- No validated strategy is enabled. `/v1/analyze` correctly remains `NO_TRADE`.
- Codal, sector, news/event, and broader liquidity/flow context are not integrated.

### Completion evidence required
1. Verified, timestamped exchange universe with explicit coverage and exclusion counts.
2. Deterministic scan of that universe with per-symbol data-quality outcomes; no silent omissions.
3. Candidate evidence and counter-evidence, with reproducible ranking and stable tie-breaking.
4. Real-data walk-forward and untouched OOS evaluation across multiple instruments, with realistic costs and adequate closed-trade sample.
5. A strategy approval record tied to exact data, code, parameters, and test results; otherwise remain `NO_TRADE`.

## Crypto spot

### Implemented
- Public Binance spot adapter and OKX fallback adapter, including paginated one-year OKX history.
- Spot-only market-data path and shared OHLCV quality checks.
- Descriptive indicators, research baseline, and research/backtest infrastructure.

### Blocking gates
- No complete exchange instrument-universe scanner or cross-asset candidate-ranking pipeline is wired into the API.
- A symbol-level successful candle fetch does not establish full market coverage.
- No strategy is validated and enabled; no actionable signal should be emitted.
- Derivatives, on-chain, funding, open interest, and other optional context are not implemented and must not be implied.

### Completion evidence required
1. Timestamped spot instrument universe from a verified exchange source, including quote-asset and market-status filters.
2. Complete per-instrument fetch/quality accounting and deterministic candidate selection.
3. Real-data walk-forward and untouched OOS validation across assets and regimes, net of costs.
4. Exact reproducibility metadata and adequate sample; otherwise return `NO_TRADE`.

## Release rule

Do not mark either market complete because endpoints respond, synthetic tests pass, or CI is green. Do not enable a strategy or present entry/stop/targets without a validated rule and current quality-passing data. The release report must name the tested commit, test run, data coverage, sample sizes, and unresolved limitations.