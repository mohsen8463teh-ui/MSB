# Baseline strategy research contract

`sma_trend_baseline_v1` is a deliberately simple long-only research baseline:
enter when the close is above SMA200 and SMA20 is above SMA50, when that
combined condition first becomes true; exit when it becomes false.

Signals are observed at candle close and must be executed at the next candle
open by the backtest engine. The baseline is not enabled in the API and is not
a recommendation. It must be evaluated on real, quality-checked data with
walk-forward and out-of-sample procedures before any live use.
