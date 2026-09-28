from decimal import Decimal

import pytest

from grandmotherbot_extension.normalization import (
    normalize_book_ticker,
    normalize_swaps,
    validate_quote_frame,
)


def test_dex_swap_normalization_preserves_identity():
    frame = normalize_swaps([{
        "tx_hash": "0xABC",
        "block_number": 100,
        "block_time": "2025-01-01T00:00:00Z",
        "dex": "uniswap",
        "pool": "0xPOOL",
        "token_in": "0xAAA",
        "token_out": "0xBBB",
        "amount_in": "1.5",
        "amount_out": "2.5",
    }])
    assert frame.iloc[0]["tx_hash"] == "0xABC"
    assert frame.iloc[0]["token_in"] == "0xaaa"
    assert frame.iloc[0]["amount_in"] == Decimal("1.5")


def test_tardis_book_ticker_normalization_uses_exchange_event_time():
    frame = normalize_book_ticker([{
        "capture_time": "2025-01-01T00:00:00.100Z",
        "message": {
            "e": "bookTicker",
            "E": 1735689600100,
            "s": "ETHUSDT",
            "b": "100.0",
            "a": "100.1",
            "B": "3",
            "A": "4",
        },
    }])
    validate_quote_frame(frame)
    assert frame.iloc[0]["symbol"] == "ETHUSDT"
    assert frame.iloc[0]["event_time"] == "2025-01-01T00:00:00.100Z"
    assert frame.iloc[0]["bid_price"] == Decimal("100.0")
    assert frame.iloc[0]["ask_qty"] == Decimal("4")
    assert frame.iloc[0]["capture_time"] == "2025-01-01T00:00:00.100Z"


def test_invalid_crossed_market_is_rejected():
    frame = normalize_book_ticker([{
        "capture_time": "2025-01-01T00:00:00Z",
        "message": {
            "e": "bookTicker",
            "E": 1735689600000,
            "s": "ETHUSDT",
            "b": "101",
            "a": "100",
            "B": "1",
            "A": "1",
        },
    }])
    with pytest.raises(ValueError):
        validate_quote_frame(frame)
