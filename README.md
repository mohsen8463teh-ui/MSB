# M.S.B

## Market Strategy Brain

M.S.B is an AI-assisted market analysis platform for Iran equities and crypto.
It is being built in independently testable stages. Passing unit tests does not
establish trading profitability or validate a strategy for live capital.

## Current verified implementation

- FastAPI health and analysis endpoints.
- Persian/English horizon parsing with explicit supported horizons.
- Fail-closed behavior when market data is missing or invalid.
- Strict OHLCV integrity checks.
- Read-only Binance public spot candle adapter for crypto spot.
- Adapter behavior tested with deterministic mocked HTTP responses.
- The API does not issue BUY/SELL signals merely because market data is available.

Live exchange connectivity, Iran market data, analysis strategy validation,
backtesting, journaling, and the user interface remain separate implementation
and verification tasks.

## Core principles

1. Understand natural-language requests without guessing unsupported horizons.
2. Verify data source, freshness, completeness, and candle integrity.
3. Never fabricate missing data or claim guaranteed profit.
4. Never use future information in historical evaluation.
5. Keep data acquisition, analysis, decision validation, and journaling separate.
6. Treat WAIT / NO_TRADE as valid outcomes.
7. Do not enable actionable signals before out-of-sample validation.
