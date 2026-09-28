from __future__ import annotations

from dataclasses import dataclass
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


def normalize_book_ticker(
    events: list[dict[str, Any]],
    *,
    symbol: str,
) -> pd.DataFrame:
    rows = []
    for event in events:
        message = event["message"]
        rows.append({
            "exchange": "binance",
            "symbol": symbol,
            "event_time": str(event["capture_time"]),
            "bid_price": Decimal(str(message["bidPrice"])),
            "ask_price": Decimal(str(message["askPrice"])),
            "bid_qty": Decimal(str(message["bidQty"])),
            "ask_qty": Decimal(str(message["askQty"])),
            "source": "tardis",
        })
    return pd.DataFrame(rows, columns=[
        "exchange", "symbol", "event_time", "bid_price", "ask_price",
        "bid_qty", "ask_qty", "source",
    ])


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
