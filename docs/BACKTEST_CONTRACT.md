# Backtest execution contract

The backtest engine accepts already-computed entry/exit booleans. A signal
observed at candle close can only execute at the next candle's open. A final
candle signal is not filled because no next open is available.

The engine is long-only, holds at most one position, uses no leverage, limits
exposure to a configured fraction of available cash, and accounts for fees and
slippage. Open positions are marked to the final close and are not silently
closed.

Accounting fields are intentionally separate:
- `realized_pnl` and `realized_return_pct` include closed trades only.
- `cash_balance` is uninvested cash; a low balance while a position is open
  is not a realized loss.
- `final_equity` and `total_return_pct` include mark-to-market value of any
  open position, before hypothetical exit costs.

This is an execution simulator, not a profitable strategy; strategy rules and
out-of-sample validation are separate requirements.
