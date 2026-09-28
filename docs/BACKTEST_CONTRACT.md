# Backtest execution contract

The backtest engine accepts already-computed entry/exit booleans. A signal
observed at candle close can only execute at the next candle's open. A final
candle signal is not filled because no next open is available.

The engine is long-only, holds at most one position, uses no leverage, limits
exposure to a configured fraction of available cash, and accounts for fees and
slippage. Open positions are marked to the final close and are not silently
closed. This is an execution simulator, not a profitable strategy; strategy
rules and out-of-sample validation are separate requirements.
