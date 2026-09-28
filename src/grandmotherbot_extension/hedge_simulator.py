from __future__ import annotations

from decimal import Decimal
from typing import Any

import pandas as pd

from .dynamic_hedge import evaluate_dynamic_hedge
from .hedge_alignment import executable_hedge_request


def simulate_hedge(
    *,
    token_amount: Decimal,
    inventory_delta: Decimal,
    mid: Decimal,
    order_book: pd.DataFrame,
    taker_fee_bps: Decimal,
    future_mid: Decimal,
) -> dict[str, Any]:
    """Simulate executable CEX hedging without redefining paper PnL.

    The paper replication remains the authoritative markout/revenue/PnL layer.
    This extension reports execution cashflow, fees, residual inventory and
    its future marked value. It does not label that total as paper PnL.
    """
    request = executable_hedge_request(
        token_amount=token_amount,
        inventory_delta=inventory_delta,
    )
    hedge = evaluate_dynamic_hedge(
        amount=Decimal(request["quantity"]),
        side=str(request["side"]),
        mid=mid,
        order_book=order_book,
        taker_fee_bps=taker_fee_bps,
    )

    filled = hedge["filled_qty"]
    execution_price = hedge["execution_price"]
    fee = hedge["cex_fee_usd"]

    inventory_sign = Decimal("1") if request["side"] == "sell" else Decimal("-1")
    hedged_inventory = inventory_sign * filled
    residual_inventory = inventory_delta - hedged_inventory

    execution_cashflow = (
        execution_price * filled
        if request["side"] == "sell"
        else -execution_price * filled
    )
    future_residual_value = residual_inventory * future_mid
    net_execution_cashflow = execution_cashflow - fee
    extension_horizon_value = net_execution_cashflow + future_residual_value

    result = dict(hedge)
    result.update({
        "side": request["side"],
        "requested_qty": Decimal(request["quantity"]),
        "future_mid": future_mid,
        "execution_cashflow_usd": execution_cashflow,
        "cex_fee_usd": fee,
        "net_execution_cashflow_usd": net_execution_cashflow,
        "hedged_inventory_qty": hedged_inventory,
        "residual_inventory_qty": residual_inventory,
        "future_residual_value_usd": future_residual_value,
        "extension_horizon_value_usd": extension_horizon_value,
        "fully_filled": hedge["unfilled_qty"] == 0,
    })
    return result
