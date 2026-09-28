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
    """Extension-only executable hedge accounting.

    future_mid must come from observed CEX data. This layer does not replace
    the paper markout methodology or modify PAPER_REPLICATION.
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
    direction = Decimal("1") if request["side"] == "sell" else Decimal("-1")

    execution_cashflow = direction * execution_price * filled
    future_inventory_value = direction * future_mid * filled
    net_hedge_value = execution_cashflow - direction * fee

    result = dict(hedge)
    result.update({
        "side": request["side"],
        "requested_qty": Decimal(request["quantity"]),
        "future_mid": future_mid,
        "execution_cashflow_usd": execution_cashflow,
        "future_inventory_value_usd": future_inventory_value,
        "net_hedge_value_usd": net_hedge_value,
        "markout_pnl_usd": future_inventory_value - net_hedge_value,
        "fully_filled": hedge["unfilled_qty"] == 0,
    })
    return result
