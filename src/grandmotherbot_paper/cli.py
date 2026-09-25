from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .constants import HORIZONS, PAPER_END_BLOCK, PAPER_START_BLOCK
from .io import load_inputs, validate_inputs
from .report import build_report
from .tardis import TardisHTTPClient, write_normalized_parquet


def _parse_utc(text: str) -> datetime:
    value = text.replace("Z", "+00:00")
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def main():
    parser = argparse.ArgumentParser(prog="grandmother-paper")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("validate")

    analyze = sub.add_parser("analyze")
    analyze.add_argument("--input", default="data/input")
    analyze.add_argument("--output", default="output")

    sub.add_parser("tardis-key-info")
    sub.add_parser("tardis-binance")

    fetch = sub.add_parser(
        "tardis-fetch",
        help="Fetch a UTC window of Binance raw Tardis data.",
    )
    fetch.add_argument("--start", required=True)
    fetch.add_argument("--end", required=True)
    fetch.add_argument("--symbols", nargs="+", required=True)
    fetch.add_argument(
        "--channels",
        nargs="+",
        default=["trade", "bookTicker"],
    )
    fetch.add_argument("--output", required=True)

    ns = parser.parse_args()

    if ns.cmd == "validate":
        root = Path("data/input")
        inputs = load_inputs(root)
        errors = validate_inputs(inputs)
        print(
            {
                "files": sorted(inputs),
                "errors": errors,
                "paper_blocks": [PAPER_START_BLOCK, PAPER_END_BLOCK],
                "horizons": len(HORIZONS),
            }
        )
        raise SystemExit(1 if errors else 0)

    if ns.cmd == "analyze":
        root = Path(ns.input)
        inputs = load_inputs(root)
        errors = validate_inputs(inputs)
        if errors:
            for error in errors:
                print(error)
            raise SystemExit(1)
        if not {"transactions", "swaps", "markouts"}.issubset(inputs):
            raise SystemExit(
                "analyze requires transactions.csv, swaps.csv and markouts.csv"
            )
        summary = build_report(str(root), ns.output)
        print(summary)
        return

    client = TardisHTTPClient()

    if ns.cmd == "tardis-key-info":
        print(json.dumps(client.get_api_key_info(), indent=2, sort_keys=True))
        return

    if ns.cmd == "tardis-binance":
        print(json.dumps(client.get_exchange_details("binance"), indent=2, sort_keys=True))
        return

    if ns.cmd == "tardis-fetch":
        start = _parse_utc(ns.start)
        end = _parse_utc(ns.end)
        events = client.normalized_window(
            start=start,
            end=end,
            symbols=ns.symbols,
            channels=ns.channels,
        )
        output = Path(ns.output)
        if output.suffix.lower() == ".parquet":
            write_normalized_parquet(events, output)
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("w", encoding="utf-8") as handle:
                for event in events:
                    handle.write(
                        json.dumps(
                            {
                                "exchange": event.exchange,
                                "channel": event.channel,
                                "symbol": event.symbol,
                                "exchange_timestamp_us": event.exchange_timestamp_us,
                                "local_timestamp_us": event.local_timestamp_us,
                                "capture_sequence": event.capture_sequence,
                                "event_type": event.event_type,
                                "trade_id": event.trade_id,
                                "book_update_id": event.book_update_id,
                                "first_update_id": event.first_update_id,
                                "final_update_id": event.final_update_id,
                                "side": event.side,
                                "price": event.price,
                                "amount": event.amount,
                                "best_bid": event.best_bid,
                                "best_bid_amount": event.best_bid_amount,
                                "best_ask": event.best_ask,
                                "best_ask_amount": event.best_ask_amount,
                                "bids": event.bids,
                                "asks": event.asks,
                                "is_snapshot": event.is_snapshot,
                                "generated": event.generated,
                                "raw_message": event.raw_message,
                            },
                            separators=(",", ":"),
                        )
                        + "\n"
                    )
        print(
            json.dumps(
                {
                    "output": str(output),
                    "events": len(events),
                    "symbols": sorted({event.symbol for event in events}),
                    "channels": sorted({event.channel for event in events}),
                    "window_start": start.isoformat(),
                    "window_end": end.isoformat(),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return


if __name__ == "__main__":
    main()
