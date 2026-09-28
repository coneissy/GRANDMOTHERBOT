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
    markout_usd: Decimal = Decimal("0"),
) -> dict[str, Any]:
    """Simulate one extension-only CEX hedge without placing an order.

    markout_usd is supplied by the caller from observed market data. No
    synthetic market movement is generated here.
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
    hedge_value = filled * mid
    execution_cost = hedge["hedge_cost_usd"]
    result = dict(hedge)
    result.update({
        "side": request["side"],
        "requested_qty": Decimal(request["quantity"]),
        "markout_usd": markout_usd,
        "markout_vs_execution_usd": markout_usd - (execution_cost - hedge_value),
        "fully_filled": hedge["unfilled_qty"] == 0,
    })
    return result
