from __future__ import annotations

from decimal import Decimal
from typing import Any

import pandas as pd


def _d(value: Any) -> Decimal:
    return Decimal(str(value))


def align_quotes_to_swaps(
    swaps: pd.DataFrame,
    quotes: pd.DataFrame,
    *,
    max_age_ms: int = 1000,
) -> pd.DataFrame:
    """Attach the latest non-stale Binance quote for the correct symbol.

    This is extension-only. It does not alter the paper markout grid or inputs.
    Swaps may provide cex_symbol explicitly. For single-symbol quote frames,
    that symbol is used as a safe convenience fallback.
    """
    required_swaps = {"tx_hash", "block_time"}
    required_quotes = {
        "event_time", "symbol", "bid_price", "ask_price", "bid_qty", "ask_qty"
    }
    if missing := required_swaps - set(swaps.columns):
        raise ValueError("swaps missing: " + ", ".join(sorted(missing)))
    if missing := required_quotes - set(quotes.columns):
        raise ValueError("quotes missing: " + ", ".join(sorted(missing)))
    if max_age_ms < 0:
        raise ValueError("max_age_ms must be non-negative")

    left = swaps.copy()
    right = quotes.copy()

    if "cex_symbol" not in left.columns:
        symbols = right["symbol"].dropna().astype(str).unique()
        if len(symbols) != 1:
            raise ValueError(
                "swaps must provide cex_symbol when quotes contain multiple symbols"
            )
        left["cex_symbol"] = str(symbols[0])

    left["_time"] = pd.to_datetime(
        left["event_time"] if "event_time" in left.columns else left["block_time"],
        utc=True,
    )
    right["_time"] = pd.to_datetime(right["event_time"], utc=True)

    left["cex_symbol"] = left["cex_symbol"].astype(str)
    right["symbol"] = right["symbol"].astype(str)

    # Prevent a quote for one token from being attached to another.
    right = right.sort_values(["symbol", "_time"])
    left = left.sort_values(["cex_symbol", "_time"])
    out = pd.merge_asof(
        left,
        right,
        left_on="_time",
        right_on="_time",
        left_by="cex_symbol",
        right_by="symbol",
        direction="backward",
        tolerance=pd.Timedelta(milliseconds=max_age_ms),
    )

    event_times = pd.to_datetime(out["event_time"], utc=True)
    out["quote_age_ms"] = (
        (out["_time"] - event_times).dt.total_seconds() * 1000
    )
    out["quote_stale"] = out["bid_price"].isna()
    out["quote_time_source"] = (
        "swap_event_time" if "event_time" in swaps.columns else "block_time"
    )
    return out.drop(columns=["_time"])


def hedge_side_from_inventory(*, inventory_delta: Decimal) -> str:
    if inventory_delta == 0:
        raise ValueError("inventory_delta cannot be zero")
    return "sell" if inventory_delta > 0 else "buy"


def executable_hedge_request(
    *,
    token_amount: Decimal,
    inventory_delta: Decimal,
) -> dict[str, Decimal | str]:
    """Convert DEX inventory into an extension-only CEX hedge request."""
    if token_amount <= 0:
        raise ValueError("token_amount must be positive")
    side = hedge_side_from_inventory(inventory_delta=inventory_delta)
    return {"side": side, "quantity": token_amount}
