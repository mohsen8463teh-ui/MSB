PROTOCOL_VERSION = "0.1.0"

SUPPORTED_HORIZONS = (
    "intraday",
    "1d",
    "3d",
    "1w",
    "1m",
    "3m",
    "5m",
    "6m",
    "1y",
)

SUPPORTED_MARKETS = (
    "iran_equity",
    "crypto_spot",
    "crypto_futures",
)

VALID_DECISIONS = (
    "BUY",
    "SELL",
    "WAIT",
    "NO_TRADE",
)

CORE_PRINCIPLES = (
    "no_fabricated_data",
    "no_guaranteed_profit",
    "no_lookahead_bias",
    "no_data_leakage",
    "no_blind_optimization",
    "data_quality_required",
    "journal_actionable_signals",
)
