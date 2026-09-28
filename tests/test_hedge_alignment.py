from decimal import Decimal

import pandas as pd
import pytest

from grandmotherbot_extension.hedge_alignment import (
    align_quotes_to_swaps,
    executable_hedge_request,
    hedge_side_from_inventory,
)


def _swap(time="2025-01-01T00:00:01Z", symbol="ETHUSDT"):
    return {
        "tx_hash": "0x1",
        "block_time": "2025-01-01T00:00:01Z",
        "event_time": time,
        "cex_symbol": symbol,
    }


def _quote(time="2025-01-01T00:00:00.900Z", symbol="ETHUSDT"):
    return {
        "event_time": time,
        "symbol": symbol,
        "bid_price": Decimal("99"),
        "ask_price": Decimal("101"),
        "bid_qty": Decimal("2"),
        "ask_qty": Decimal("3"),
    }


def test_latest_non_stale_quote_is_attached():
    out = align_quotes_to_swaps(
        pd.DataFrame([_swap()]),
        pd.DataFrame([_quote()]),
        max_age_ms=200,
    )
    assert out.iloc[0]["ask_price"] == Decimal("101")
    assert out.iloc[0]["quote_stale"] is False
    assert out.iloc[0]["alignment_method"] == "backward_latest_same_symbol"


def test_stale_quote_is_not_used():
    out = align_quotes_to_swaps(
        pd.DataFrame([_swap()]),
        pd.DataFrame([_quote(time="2025-01-01T00:00:00Z")]),
        max_age_ms=50,
    )
    assert pd.isna(out.iloc[0]["bid_price"])
    assert out.iloc[0]["quote_stale"] is True


def test_cross_symbol_quotes_are_never_attached():
    out = align_quotes_to_swaps(
        pd.DataFrame([_swap(symbol="ETHUSDT")]),
        pd.DataFrame([_quote(symbol="BTCUSDT")]),
        max_age_ms=1000,
    )
    assert pd.isna(out.iloc[0]["bid_price"])


def test_explicit_event_time_is_required():
    swaps = pd.DataFrame([{
        "tx_hash": "0x1",
        "block_time": "2025-01-01T00:00:01Z",
        "cex_symbol": "ETHUSDT",
    }])
    with pytest.raises(ValueError):
        align_quotes_to_swaps(swaps, pd.DataFrame([_quote()]))


def test_hedge_direction_offsets_inventory():
    assert hedge_side_from_inventory(inventory_delta=Decimal("2")) == "sell"
    assert hedge_side_from_inventory(inventory_delta=Decimal("-2")) == "buy"
    assert executable_hedge_request(
        token_amount=Decimal("2"), inventory_delta=Decimal("2")
    ) == {"side": "sell", "quantity": Decimal("2")}


def test_zero_inventory_is_rejected():
    with pytest.raises(ValueError):
        hedge_side_from_inventory(inventory_delta=Decimal("0"))
