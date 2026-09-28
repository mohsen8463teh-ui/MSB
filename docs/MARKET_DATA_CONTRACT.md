# Market data contract

All market-data adapters must normalize candle data to this shape:

- `timestamp`: Unix seconds (UTC)
- `open`, `high`, `low`, `close`: finite positive numbers
- `volume`: finite non-negative number

Before analysis, call `validate_ohlcv`. It does not repair or guess missing prices.
A malformed candle makes the series invalid. An expected-interval gap makes it
incomplete. For markets with scheduled closures or irregular sessions, omit
`interval_seconds` and apply a market-specific calendar validator instead.

A provider must not mark data as usable merely because a response was received.
It must verify source, timestamp freshness, completeness, and candle integrity.
Until a live provider supplies verified data, the API remains fail-closed and
returns `NO_TRADE`.
