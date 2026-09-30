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
- Append-only SQLite research journal with create/list/get API; records are
  NO_TRADE only, and TEST/FIXTURE records cannot claim live timestamps.
- Informational long-only position-size calculator capped by risk budget,
  available cash, and exposure; it does not authorize or submit orders.
- Automated tests run in GitHub Actions.
- GitHub-hosted runner probe: OKX returned data, but TSETMC requests timed out
  or failed to connect from that runner. This is a runner-network limitation;
  a green workflow does not certify live TSETMC connectivity.

## Run locally on Android / Termux (Iran equities)

The TSETMC provider must execute from a network that can reach TSETMC. The
successful Termux provider test confirms that the phone can reach it; GitHub
Actions runs on separate hosted infrastructure and cannot use the phone's
network.

From the repository root, with the project virtual environment activated:

```bash
bash scripts/run_local_termux.sh
```

Then open this address in the browser on the same phone:

`http://127.0.0.1:8000/`

The script uses `.venv/bin/python` when available, checks runtime dependencies,
and starts the existing FastAPI app bound to localhost only. Keep the Termux
session running while using the dashboard. Stop it with Ctrl+C. The analysis
request for an Iran equity symbol (for example, `فملی`) is then fetched by the
API running on the phone, so TSETMC traffic originates from Termux rather than
a GitHub runner. No external relay, VPS, or fabricated fallback data is used.

If the dashboard is hosted on a remote server instead, this local-only setup
does not automatically connect that server to the phone. A secure relay or a
deployment inside a reachable network would be a separate requirement; do not
expose a public unauthenticated data-ingest endpoint.

## Core principles

1. Understand natural-language requests without guessing unsupported horizons.
2. Verify data source, freshness, completeness, and candle integrity.
3. Never fabricate missing data or claim guaranteed profit.
4. Never use future information in historical evaluation.
5. Keep data acquisition, analysis, decision validation, and journaling separate.
6. Treat WAIT / NO_TRADE as valid outcomes.
7. Do not enable actionable signals before out-of-sample validation.
