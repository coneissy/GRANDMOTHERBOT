from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class NormalizedDexTrade:
    tx_hash: str
    block_number: int
    block_time: str
    dex: str
    pool: str
    token_in: str
    token_out: str
    amount_in: Decimal
    amount_out: Decimal


@dataclass(frozen=True)
class NormalizedCexQuote:
    exchange: str
    symbol: str
    event_time: str
    bid_price: Decimal
    ask_price: Decimal
    bid_qty: Decimal
    ask_qty: Decimal
    source: str = "tardis"


def normalize_swaps(rows: list[dict[str, Any]]) -> pd.DataFrame:
    columns = [
        "tx_hash", "block_number", "block_time", "dex", "pool",
        "token_in", "token_out", "amount_in", "amount_out",
    ]
    normalized = []
    for row in rows:
        normalized.append({
            "tx_hash": str(row["tx_hash"]),
            "block_number": int(row["block_number"]),
            "block_time": str(row["block_time"]),
            "dex": str(row["dex"]),
            "pool": str(row["pool"]),
            "token_in": str(row["token_in"]).lower(),
            "token_out": str(row["token_out"]).lower(),
            "amount_in": Decimal(str(row["amount_in"])),
            "amount_out": Decimal(str(row["amount_out"])),
        })
    return pd.DataFrame(normalized, columns=columns)


def _event_time_from_binance_message(message: dict[str, Any]) -> str:
    event_ms = message.get("E")
    if event_ms is None:
        raise ValueError("Binance bookTicker message missing exchange event time E")
    timestamp = datetime.fromtimestamp(
        int(event_ms) / 1000,
        tz=timezone.utc,
    )
    return timestamp.isoformat().replace("+00:00", "Z")


def normalize_book_ticker(
    events: list[dict[str, Any]],
    *,
    symbol: str | None = None,
) -> pd.DataFrame:
    """Normalize Binance Spot native bookTicker messages.

    Tardis capture_time is retained separately from Binance's exchange event
    time. Prices and quantities are parsed from Binance native fields b/B/a/A.
    """
    columns = [
        "exchange", "symbol", "event_time", "capture_time",
        "bid_price", "ask_price", "bid_qty", "ask_qty", "source",
    ]
    rows = []
    for event in events:
        if event.get("disconnect"):
            continue
        message = event["message"]
        if message.get("e") not in (None, "bookTicker"):
            continue
        message_symbol = message.get("s")
        if symbol is not None and message_symbol not in (None, symbol):
            continue
        resolved_symbol = str(message_symbol or symbol or "")
        if not resolved_symbol:
            raise ValueError("Binance bookTicker event missing symbol")
        rows.append({
            "exchange": "binance",
            "symbol": resolved_symbol,
            "event_time": _event_time_from_binance_message(message),
            "capture_time": str(event["capture_time"]),
            "bid_price": Decimal(str(message["b"])),
            "ask_price": Decimal(str(message["a"])),
            "bid_qty": Decimal(str(message["B"])),
            "ask_qty": Decimal(str(message["A"])),
            "source": "tardis",
        })
    return pd.DataFrame(rows, columns=columns)


def validate_quote_frame(frame: pd.DataFrame) -> None:
    required = {
        "exchange", "symbol", "event_time", "bid_price", "ask_price",
        "bid_qty", "ask_qty", "source",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError("quote frame missing: " + ", ".join(sorted(missing)))
    if (frame["bid_price"] <= 0).any() or (frame["ask_price"] <= 0).any():
        raise ValueError("quote prices must be positive")
    if (frame["bid_price"] > frame["ask_price"]).any():
        raise ValueError("bid cannot exceed ask")
    if (frame["bid_qty"] < 0).any() or (frame["ask_qty"] < 0).any():
        raise ValueError("quote quantities cannot be negative")
