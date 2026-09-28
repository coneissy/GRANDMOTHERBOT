from decimal import Decimal

import pytest

from grandmotherbot_extension.normalization import (
    dex_event_time,
    dex_order_key,
    normalize_book_ticker,
    normalize_swaps,
    validate_quote_frame,
)


def test_dex_swap_normalization_preserves_identity_and_ordering():
    frame = normalize_swaps([
        {
            "tx_hash": "0x2", "block_number": 100, "block_time": "2025-01-01T00:00:00Z",
            "tx_index": 2, "log_index": 9, "dex": "uniswap", "pool": "0xPOOL",
            "token_in": "0xAAA", "token_out": "0xBBB", "amount_in": "1.5", "amount_out": "2.5",
        },
        {
            "tx_hash": "0x1", "block_number": 100, "block_time": "2025-01-01T00:00:00Z",
            "tx_index": 1, "log_index": 7, "dex": "uniswap", "pool": "0xPOOL",
            "token_in": "0xAAA", "token_out": "0xBBB", "amount_in": "3", "amount_out": "4",
        },
    ])
    assert frame.iloc[0]["tx_hash"] == "0x1"
    assert frame.iloc[1]["tx_hash"] == "0x2"
    assert frame.iloc[0]["token_in"] == "0xaaa"
    assert frame.iloc[0]["amount_in"] == Decimal("3")


def test_dex_order_key_requires_source_order_fields():
    assert dex_order_key({
        "block_number": 100, "tx_index": 2, "log_index": 9,
    }) == (100, 2, 9)
    with pytest.raises(ValueError):
        dex_order_key({"block_number": 100, "tx_index": 2})


def test_dex_event_time_never_interpolates():
    row = {"block_time": "2025-01-01T00:00:00Z"}
    assert dex_event_time(row) == "2025-01-01T00:00:00Z"
    row["event_time"] = "2025-01-01T00:00:00.123Z"
    assert dex_event_time(row) == "2025-01-01T00:00:00.123Z"


def test_tardis_book_ticker_normalization_uses_exchange_event_time():
    frame = normalize_book_ticker([{
        "capture_time": "2025-01-01T00:00:00.100Z",
        "message": {
            "e": "bookTicker", "E": 1735689600100, "s": "ETHUSDT",
            "b": "100.0", "a": "100.1", "B": "3", "A": "4",
        },
    }])
    validate_quote_frame(frame)
    assert frame.iloc[0]["symbol"] == "ETHUSDT"
    assert frame.iloc[0]["event_time"] == "2025-01-01T00:00:00.100Z"
    assert frame.iloc[0]["bid_price"] == Decimal("100.0")
    assert frame.iloc[0]["ask_qty"] == Decimal("4")


def test_invalid_crossed_market_is_rejected():
    frame = normalize_book_ticker([{
        "capture_time": "2025-01-01T00:00:00Z",
        "message": {
            "e": "bookTicker", "E": 1735689600000, "s": "ETHUSDT",
            "b": "101", "a": "100", "B": "1", "A": "1",
        },
    }])
    with pytest.raises(ValueError):
        validate_quote_frame(frame)
