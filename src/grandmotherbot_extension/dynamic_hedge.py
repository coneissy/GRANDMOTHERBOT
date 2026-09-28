from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

import pandas as pd


@dataclass(frozen=True)
class HedgeObservation:
    """An extension-only hedge observation."""

    horizon_s: Decimal
    token_usdt_mid: Decimal
    hedge_price: Decimal
    executable_qty: Decimal
    estimated_slippage_bps: Decimal
    cex_fee_usd: Decimal


def _d(value) -> Decimal:
    return Decimal(str(value))


def dynamic_horizons(
    start_s: float = -1.0,
    end_s: float = 10.0,
    step_s: float = 0.25,
) -> tuple[Decimal, ...]:
    """Build an extension-only horizon grid.

    The paper's -1..10/0.5 grid is never changed by this function.
    """
    if step_s <= 0:
        raise ValueError("step_s must be positive")
    start, end, step = _d(start_s), _d(end_s), _d(step_s)
    if end < start:
        raise ValueError("end_s must be >= start_s")

    points = []
    current = start
    while current <= end:
        points.append(current)
        current += step
    return tuple(points)


def executable_price_from_book(
    book: pd.DataFrame,
    side: str,
    quantity: Decimal,
) -> tuple[Decimal, Decimal]:
    """Return VWAP and filled quantity from a level-2 order book.

    Expected columns: price, quantity. Buy consumes asks; sell consumes bids.
    """
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    side = side.lower()
    if side not in {"buy", "sell"}:
        raise ValueError("side must be buy or sell")

    required = {"price", "quantity"}
    missing = required - set(book.columns)
    if missing:
        raise ValueError("order book missing: " + ", ".join(sorted(missing)))

    work = book.copy()
    work["price"] = work["price"].map(_d)
    work["quantity"] = work["quantity"].map(_d)
    work = work[(work["price"] > 0) & (work["quantity"] > 0)]
    work = work.sort_values("price", ascending=(side == "buy"))

    remaining = quantity
    notional = Decimal("0")
    filled = Decimal("0")
    for _, row in work.iterrows():
        take = min(remaining, row["quantity"])
        notional += take * row["price"]
        filled += take
        remaining -= take
        if remaining <= 0:
            break

    if filled <= 0:
        raise ValueError("order book has no executable liquidity")
    return notional / filled, filled


def slippage_bps(mid: Decimal, execution_price: Decimal) -> Decimal:
    if mid <= 0:
        raise ValueError("mid must be positive")
    return abs(execution_price - mid) / mid * Decimal("10000")


def evaluate_dynamic_hedge(
    *,
    amount: Decimal,
    side: str,
    mid: Decimal,
    order_book: pd.DataFrame,
    taker_fee_bps: Decimal,
) -> dict[str, Decimal]:
    """Estimate hedge cost from executable liquidity and taker fees."""
    execution_price, filled = executable_price_from_book(order_book, side, amount)
    fee = filled * execution_price * taker_fee_bps / Decimal("10000")
    slip = slippage_bps(mid, execution_price)
    return {
        "mid": mid,
        "execution_price": execution_price,
        "filled_qty": filled,
        "unfilled_qty": amount - filled,
        "slippage_bps": slip,
        "cex_fee_usd": fee,
        "hedge_cost_usd": execution_price * filled + fee,
    }


def dynamic_markout(observations: Iterable[HedgeObservation]) -> pd.DataFrame:
    """Normalize extension observations without touching paper markouts."""
    rows = [{
        "horizon_s": float(o.horizon_s),
        "token_usdt_mid": float(o.token_usdt_mid),
        "hedge_price": float(o.hedge_price),
        "executable_qty": float(o.executable_qty),
        "estimated_slippage_bps": float(o.estimated_slippage_bps),
        "cex_fee_usd": float(o.cex_fee_usd),
    } for o in observations]
    return pd.DataFrame(rows, columns=[
        "horizon_s", "token_usdt_mid", "hedge_price",
        "executable_qty", "estimated_slippage_bps", "cex_fee_usd",
    ])


def choose_dynamic_horizon(curve: pd.DataFrame) -> Decimal:
    """Choose the extension horizon maximizing net hedge value."""
    required = {"horizon_s", "markout_usd", "cex_fee_usd", "slippage_cost_usd"}
    missing = required - set(curve.columns)
    if missing:
        raise ValueError("curve missing: " + ", ".join(sorted(missing)))
    if curve.empty:
        raise ValueError("curve is empty")

    work = curve.copy()
    work["objective"] = (
        work["markout_usd"] - work["cex_fee_usd"] - work["slippage_cost_usd"]
    )
    best = work.sort_values(
        ["objective", "horizon_s"], ascending=[False, True]
    ).iloc[0]
    return _d(best["horizon_s"])
