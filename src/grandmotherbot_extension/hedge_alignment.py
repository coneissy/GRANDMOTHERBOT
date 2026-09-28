from __future__ import annotations

from decimal import Decimal

import pandas as pd


def align_quotes_to_swaps(
    swaps: pd.DataFrame,
    quotes: pd.DataFrame,
    *,
    max_age_ms: int = 1000,
) -> pd.DataFrame:
    """Attach the latest non-stale Binance quote using explicit event time."""
    required_swaps = {"tx_hash", "block_time", "event_time", "cex_symbol"}
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
    left["_time"] = pd.to_datetime(left["event_time"], utc=True)
    right["_time"] = pd.to_datetime(right["event_time"], utc=True)

    if left["_time"].isna().any() or right["_time"].isna().any():
        raise ValueError("event_time cannot be null for executable alignment")

    left["cex_symbol"] = left["cex_symbol"].astype(str).str.upper()
    right["symbol"] = right["symbol"].astype(str).str.upper()

    # pandas merge_asof requires the time key itself to be globally sorted,
    # even when a by-key partitions the matching operation.
    right = right.sort_values(["_time", "symbol"]).reset_index(drop=True)
    left = left.sort_values(["_time", "cex_symbol"]).reset_index(drop=True)

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

    out["quote_age_ms"] = (
        (out["_time"] - pd.to_datetime(out["event_time_y"], utc=True))
        .dt.total_seconds() * 1000
    )
    out["quote_stale"] = out["bid_price"].isna()
    out["quote_time_source"] = "dex_event_time"
    out["alignment_method"] = "backward_latest_same_symbol"
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
    if token_amount <= 0:
        raise ValueError("token_amount must be positive")
    side = hedge_side_from_inventory(inventory_delta=inventory_delta)
    return {"side": side, "quantity": token_amount}
