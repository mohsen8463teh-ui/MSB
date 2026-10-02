# MSB Analysis Contract

Status: implementation specification; not a validated trading strategy.

## Objective
Provide evidence-grounded market analysis for Iran equities and crypto spot across horizons from one day through one year. The system may return NO_TRADE. It must not promise returns, fabricate evidence, or turn missing data into a directional call.

## Canonical request
Every analysis run must resolve and persist:
- market: iran_equity or crypto_spot (futures remain disabled until separately implemented and validated)
- horizon: 1d, 3d, 1w, 1m, 3m, 5m, 6m, or 1y; reject ambiguity
- universe definition and eligibility rules; explicit symbol when user asks about one
- as-of timestamp, timezone, data-source identifiers, candle interval, and exact data snapshot/hash
- risk profile and constraints, including long-only equity constraints
- protocol, strategy, prompt, and model versions when applicable

## Canonical response
Return machine-readable fields:
- decision: BUY, WAIT, or NO_TRADE (SELL is not an instruction to short; for long-only markets it means exit/avoid only when a held position context exists)
- market, symbol, horizon, as_of, data lineage, freshness/completeness
- ranked candidates with comparable evidence and reasons for exclusions
- thesis, supporting evidence, counter-evidence, uncertainty, and invalidation conditions
- entry zone, stop, targets, expected holding horizon, risk/reward, and sizing only when a validated strategy can calculate them
- explicit NO_TRADE reason when quality, evidence, or validation gates fail

## Decision boundaries
1. Data acquisition and validation are separate from interpretation.
2. Deterministic calculations (prices, indicators, sizing, risk limits) are computed by tested code, never invented by a language model.
3. The reasoning layer may explain only evidence present in the run context; every factual claim must map to evidence.
4. Candidate ranking is market-wide within a documented eligible universe, not a hindsight-selected ticker.
5. Iran equities are long-only. No short recommendation is generated.
6. A baseline indicator or a high score is not by itself a validated trading edge.
7. No actionable entry/stop/target is emitted until a strategy has passed chronological out-of-sample evaluation and execution-cost assumptions.
8. All horizons are evaluated independently; success at one horizon does not validate another.
9. If data is stale, incomplete, ambiguous, or inconsistent, fail closed to NO_TRADE.
10. No live order execution is in scope until separately authorized and risk-controlled.

## ChatGPT/MSB parity evaluation
A comparison is meaningful only when both systems receive the same timestamped market snapshot, eligible universe, user intent, horizon, and risk constraints. Record model/prompt versions and repeat runs. Compare:
- top-choice overlap and rank stability
- evidence coverage and factual support
- entry/stop/target differences where actionable outputs are permitted
- abstention quality (whether NO_TRADE is appropriate)
Do not claim exact parity with the consumer ChatGPT product, whose model, tools, context, and data may differ.

## Release gates
- Unit and integration tests pass.
- No lookahead, leakage, or survivorship contamination in evaluation.
- Real market data, transaction costs, slippage, and chronological splits are used.
- Each horizon/market has sufficient out-of-sample closed trades and documented uncertainty.
- No live signal is enabled merely because code or tests pass.
- Known limitations and unsupported markets are explicit in the UI and API.

## Current baseline status
The current API calculates descriptive indicators and intentionally returns NO_TRADE because no validated actionable strategy is enabled. This contract does not change that behavior; it defines the target interface and safety gates for subsequent implementation.
