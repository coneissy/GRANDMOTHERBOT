from decimal import Decimal

import pandas as pd

from grandmotherbot_extension.hedge_simulator import simulate_hedge


def test_simulator_uses_executable_price_fee_and_partial_fill():
    book = pd.DataFrame([
        {"price": Decimal("101"), "quantity": Decimal("1")},
    ])
    result = simulate_hedge(
        token_amount=Decimal("2"),
        inventory_delta=Decimal("2"),
        mid=Decimal("100"),
        order_book=book,
        taker_fee_bps=Decimal("15"),
        markout_usd=Decimal("5"),
    )

    assert result["side"] == "sell"
    assert result["requested_qty"] == Decimal("2")
    assert result["filled_qty"] == Decimal("1")
    assert result["unfilled_qty"] == Decimal("1")
    assert result["fully_filled"] is False
    assert result["cex_fee_usd"] == Decimal("0.1515")
    assert result["markout_vs_execution_usd"] == Decimal("4.8485")
