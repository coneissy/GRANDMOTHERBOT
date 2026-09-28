from decimal import Decimal

import pandas as pd
import pytest

from grandmotherbot_extension.dynamic_hedge import (
    choose_dynamic_horizon,
    dynamic_horizons,
    evaluate_dynamic_hedge,
    executable_price_from_book,
)


def test_extension_horizons_do_not_change_paper_grid():
    assert dynamic_horizons()[:3] == (
        Decimal("-1.0"),
        Decimal("-0.75"),
        Decimal("-0.50"),
    )


def test_dynamic_horizon_optimizes_net_value():
    curve = pd.DataFrame([
        {"horizon_s": 1.0, "markout_usd": 10, "cex_fee_usd": 1, "slippage_cost_usd": 2},
        {"horizon_s": 2.0, "markout_usd": 12, "cex_fee_usd": 1, "slippage_cost_usd": 1},
        {"horizon_s": 3.0, "markout_usd": 14, "cex_fee_usd": 2, "slippage_cost_usd": 4},
    ])
    assert choose_dynamic_horizon(curve) == Decimal("2.0")


def test_order_book_vwap_and_partial_fill():
    book = pd.DataFrame([
        {"price": 101, "quantity": 2},
        {"price": 100, "quantity": 1},
    ])
    vwap, filled = executable_price_from_book(book, "buy", Decimal("2"))
    assert vwap == Decimal("100.5")
    assert filled == Decimal("2")


def test_dynamic_hedge_includes_taker_fee_and_slippage():
    book = pd.DataFrame([
        {"price": 101, "quantity": 2},
    ])
    result = evaluate_dynamic_hedge(
        amount=Decimal("1"),
        side="buy",
        mid=Decimal("100"),
        order_book=book,
        taker_fee_bps=Decimal("15"),
    )
    assert result["execution_price"] == Decimal("101")
    assert result["slippage_bps"] == Decimal("100")
    assert result["cex_fee_usd"] == Decimal("0.1515")


def test_invalid_book_is_rejected():
    with pytest.raises(ValueError):
        executable_price_from_book(
            pd.DataFrame([{"price": 100}]),
            "buy",
            Decimal("1"),
        )
