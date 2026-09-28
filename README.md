# M.S.B

## Market Strategy Brain

M.S.B is an AI-assisted market analysis platform for Iran equities and crypto.
It is being built in independently testable stages. Passing unit tests does not
establish trading profitability or validate a strategy for live capital.

## Current verified implementation

- FastAPI health and analysis endpoints plus a local Persian RTL web dashboard.
- Persian/English horizon parsing with explicit supported horizons.
- Fail-closed behavior when market data is missing or invalid.
- Strict OHLCV integrity checks.
- Read-only Binance and OKX public spot candle adapters with automatic fallback.
- Read-only TSETMC daily-history adapter with exact-symbol matching.
- Today's potentially unfinished TSETMC candle is excluded.
- SMA20/50/200, Wilder RSI14, Wilder ATR14, momentum, volume ratio,
  support/resistance, breakout, and descriptive regime/evidence labels.
- Research-only SMA trend baseline, next-open backtest engine, and fixed
  chronological holdout evaluator. None is enabled as a live signal.
- Backtest reporting separates closed-trade realized PnL from open-position
  mark-to-market equity and uninvested cash.
- 64 automated tests pass in GitHub Actions (one dependency deprecation warning).
- Live GitHub-runner probe: OKX returned 399 complete daily candles for the
  one-year request; the API produced indicators and remained NO_TRADE.
  The fixed 120-bar holdout had zero closed trades and therefore no realized
  strategy result. Binance returned HTTP 451; TSETMC timed out from that runner.

Live connectivity from the user's own network, Iran market coverage, strategy
validation, robust multi-asset walk-forward testing, journaling, and the full
AI assistant interface remain separate implementation and verification tasks.

## Core principles

1. Understand natural-language requests without guessing unsupported horizons.
2. Verify data source, freshness, completeness, and candle integrity.
3. Never fabricate missing data or claim guaranteed profit.
4. Never use future information in historical evaluation.
5. Keep data acquisition, analysis, decision validation, and journaling separate.
6. Treat WAIT / NO_TRADE as valid outcomes.
7. Do not enable actionable signals before out-of-sample validation.
