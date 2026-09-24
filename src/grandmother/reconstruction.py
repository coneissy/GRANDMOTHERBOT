from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from dataclasses import dataclass

from .models import PoolSwap


@dataclass(frozen=True)
class EffectiveTrade:
    token_a: str
    token_b: str
    amount_a: Decimal
    amount_b: Decimal
    volume_token_a_usd: Decimal


def reconstruct_effective_trade(
    swaps: tuple[PoolSwap, ...],
    token_usdt_mid: dict[str, Decimal],
) -> EffectiveTrade:
    """Aggregate sequential swaps into the effective terminal token pair.

    The method follows the paper's multi-swap reconstruction idea: intermediate
    tokens are internal to the transaction; only the net external pair remains.
    """
    if not swaps:
        raise ValueError("at least one swap is required")

    net = defaultdict(Decimal)
    for s in swaps:
        net[s.token_in] -= s.amount_in
        net[s.token_out] += s.amount_out

    positives = [(t, q) for t, q in net.items() if q > 0]
    negatives = [(t, -q) for t, q in net.items() if q < 0]

    if len(positives) != 1 or len(negatives) != 1:
        raise ValueError("transaction must settle to one net buy and one net sell token")

    buy_token, amount_a = positives[0]
    sell_token, amount_b = negatives[0]
    if buy_token not in token_usdt_mid or sell_token not in token_usdt_mid:
        raise ValueError("USDT mid-price missing for effective tokens")

    volume_usd = amount_a * token_usdt_mid[buy_token]
    return EffectiveTrade(
        token_a=buy_token,
        token_b=sell_token,
        amount_a=amount_a,
        amount_b=amount_b,
        volume_token_a_usd=volume_usd,
    )
