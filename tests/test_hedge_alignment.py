from decimal import Decimal

import pandas as pd
import pytest

from grandmotherbot_extension.hedge_alignment import (
    align_quotes_to_swaps,
    executable_hedge_request,
    hedge_side_from_inventory,
)


def test_latest_non_stale_quote_is_attached():
    swaps = pd.DataFrame([{
        "tx_hash": "0x1",
        "block_time": "2025-01-01T00:00:01Z",
    }])
    quotes = pd.DataFrame([{
        "event_time": "2025-01-01T00:00:00.900Z",
        "symbol": "ETHUSDT",
        "bid_price": Decimal("99"),
        "ask_price": Decimal("101"),
        "bid_qty": Decimal("2"),
        "ask_qty": Decimal("3"),
    }])
    out = align_quotes_to_swaps(swaps, quotes, max_age_ms=200)
    assert out.iloc[0]["ask_price"] == Decimal("101")
    assert out.iloc[0]["quote_stale"] is False


def test_stale_quote_is_not_used():
    swaps = pd.DataFrame([{
        "tx_hash": "0x1",
        "block_time": "2025-01-01T00:00:02Z",
    }])
    quotes = pd.DataFrame([{
        "event_time": "2025-01-01T00:00:00Z",
        "symbol": "ETHUSDT",
        "bid_price": Decimal("99"),
        "ask_price": Decimal("101"),
        "bid_qty": Decimal("2"),
        "ask_qty": Decimal("3"),
    }])
    out = align_quotes_to_swaps(swaps, quotes, max_age_ms=500)
    assert pd.isna(out.iloc[0]["bid_price"])
    assert out.iloc[0]["quote_stale"] is True


def test_hedge_direction_offsets_inventory():
    assert hedge_side_from_inventory(inventory_delta=Decimal("2")) == "sell"
    assert hedge_side_from_inventory(inventory_delta=Decimal("-2")) == "buy"
    assert executable_hedge_request(
        token_amount=Decimal("2"), inventory_delta=Decimal("2")
    ) == {"side": "sell", "quantity": Decimal("2")}


def test_zero_inventory_is_rejected():
    with pytest.raises(ValueError):
        hedge_side_from_inventory(inventory_delta=Decimal("0"))
