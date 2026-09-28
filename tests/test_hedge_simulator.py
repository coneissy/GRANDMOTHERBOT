from decimal import Decimal

import pandas as pd
import pytest

from grandmotherbot_extension.hedge_simulator import simulate_hedge
from grandmotherbot_extension.hedge_alignment import align_quotes_to_swaps


def test_simulator_reports_execution_and_residual_inventory_separately_from_paper_pnl():
    book = pd.DataFrame([
        {"price": Decimal("101"), "quantity": Decimal("1")},
    ])
    result = simulate_hedge(
        token_amount=Decimal("2"),
        inventory_delta=Decimal("2"),
        mid=Decimal("100"),
        order_book=book,
        taker_fee_bps=Decimal("15"),
        future_mid=Decimal("102"),
    )

    assert result["side"] == "sell"
    assert result["requested_qty"] == Decimal("2")
    assert result["filled_qty"] == Decimal("1")
    assert result["unfilled_qty"] == Decimal("1")
    assert not bool(result["fully_filled"])
    assert result["cex_fee_usd"] == Decimal("0.1515")
    assert result["residual_inventory_qty"] == Decimal("1")
    assert result["future_residual_value_usd"] == Decimal("102")
    assert result["net_execution_cashflow_usd"] == Decimal("100.8485")
    assert result["extension_horizon_value_usd"] == Decimal("202.8485")
    assert "markout_pnl_usd" not in result


def test_quote_alignment_does_not_cross_symbols():
    swaps = pd.DataFrame([
        {
            "tx_hash": "0x1",
            "block_time": "2025-01-01T00:00:01Z",
            "event_time": "2025-01-01T00:00:01Z",
            "cex_symbol": "ETHUSDT",
        },
    ])
    quotes = pd.DataFrame([
        {
            "event_time": "2025-01-01T00:00:00.900Z",
            "symbol": "BTCUSDT",
            "bid_price": Decimal("99999"),
            "ask_price": Decimal("100001"),
            "bid_qty": Decimal("2"),
            "ask_qty": Decimal("3"),
        },
        {
            "event_time": "2025-01-01T00:00:00.800Z",
            "symbol": "ETHUSDT",
            "bid_price": Decimal("99"),
            "ask_price": Decimal("101"),
            "bid_qty": Decimal("2"),
            "ask_qty": Decimal("3"),
        },
    ])
    out = align_quotes_to_swaps(swaps, quotes, max_age_ms=300)
    assert out.iloc[0]["symbol"] == "ETHUSDT"
    assert out.iloc[0]["ask_price"] == Decimal("101")


def test_multi_symbol_quotes_require_explicit_swap_symbol():
    swaps = pd.DataFrame([{
        "tx_hash": "0x1",
        "block_time": "2025-01-01T00:00:01Z",
        "cex_symbol": "ETHUSDT",
    }])
    quotes = pd.DataFrame([
        {
            "event_time": "2025-01-01T00:00:00.900Z",
            "symbol": "ETHUSDT",
            "bid_price": Decimal("99"),
            "ask_price": Decimal("101"),
            "bid_qty": Decimal("2"),
            "ask_qty": Decimal("3"),
        },
        {
            "event_time": "2025-01-01T00:00:00.900Z",
            "symbol": "BTCUSDT",
            "bid_price": Decimal("99999"),
            "ask_price": Decimal("100001"),
            "bid_qty": Decimal("2"),
            "ask_qty": Decimal("3"),
        },
    ])
    with pytest.raises(ValueError):
        align_quotes_to_swaps(swaps, quotes)
