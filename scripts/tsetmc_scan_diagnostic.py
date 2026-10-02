"""Run a bounded, read-only TSETMC scan and print quality diagnostics.

Usage (from repository root, with the project venv active):
    python scripts/tsetmc_scan_diagnostic.py --limit 5 --offset 5 --horizon 1w
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.analysis.tsetmc_scanner import TsetmcMarketScanner


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=5, help="symbols to inspect (1-20)")
    parser.add_argument("--offset", type=int, default=0, help="skip this many symbols in source order")
    parser.add_argument("--concurrency", type=int, default=1, help="parallel requests (1-2)")
    parser.add_argument(
        "--horizon", choices=("1d", "3d", "1w", "1m", "3m", "5m", "6m", "1y"),
        default="1w",
    )
    args = parser.parse_args()
    if not 1 <= args.limit <= 20:
        parser.error("--limit must be between 1 and 20 for this diagnostic")
    if args.offset < 0:
        parser.error("--offset must be non-negative")
    if not 1 <= args.concurrency <= 2:
        parser.error("--concurrency must be 1 or 2")
    return args


async def main():
    args = parse_args()
    result = await TsetmcMarketScanner().scan(
        horizon=args.horizon, limit=args.limit, concurrency=args.concurrency, offset=args.offset
    )
    # Keep the report focused; never emit full candle histories.
    report = {
        "status": result.get("status"),
        "coverage": result.get("coverage"),
        "horizon": result.get("horizon"),
        "candidate_count": result.get("candidate_count"),
        "candidates": [
            {
                "symbol": item.get("symbol"),
                "instrument_id": item.get("instrument_id"),
                "data_as_of": item.get("data_as_of"),
                "source": item.get("source"),
                "decision": item.get("decision"),
                "score_is_signal": item.get("score_is_signal"),
            }
            for item in result.get("candidates", [])
        ],
        "rejection_issue_counts": result.get("rejection_issue_counts"),
        "quality_summary": result.get("quality_summary"),
        "rejected": result.get("rejected"),
        "universe_issues": result.get("universe_issues"),
        "research_only": result.get("research_only"),
        "notice": result.get("notice"),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(json.dumps({"status": "INTERRUPTED", "notice": "Scan cancelled by user."}, ensure_ascii=False))
        raise SystemExit(130)
    except Exception as exc:
        print(json.dumps({
            "status": "SCAN_ERROR",
            "error_type": type(exc).__name__,
            "error": str(exc)[:240],
            "notice": "No trading action was taken. Check network access and TSETMC availability.",
        }, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(2)
