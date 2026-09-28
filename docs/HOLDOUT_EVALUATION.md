# Fixed holdout evaluation contract

The fixed chronological holdout evaluator reserves a later contiguous segment
for testing. Earlier candles are used only to warm up the SMA indicators; no
parameters are fitted on the holdout. The test begins flat. If the baseline
condition is already true at the first test candle's close, the evaluator
schedules entry at the next open.

This is not walk-forward optimization, does not establish statistical edge,
and must not be used as a live trading approval. Report closed trades and open
positions separately; mark-to-market return on an open position is not realized
profit.
