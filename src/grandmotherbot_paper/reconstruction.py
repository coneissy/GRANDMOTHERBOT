from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class Swap:
    token_in: str
    token_out: str
    amount_in: Decimal
    amount_out: Decimal

@dataclass(frozen=True)
class EffectiveTrade:
    token_bought: str
    amount_bought: Decimal
    token_sold: str
    amount_sold: Decimal

def reconstruct_effective_trade(swaps: tuple[Swap, ...]) -> EffectiveTrade:
    if not swaps:
        raise ValueError("at least one swap is required")
    net = defaultdict(Decimal)
    for s in swaps:
        net[s.token_in] -= s.amount_in
        net[s.token_out] += s.amount_out
    bought = [(t, q) for t, q in net.items() if q > 0]
    sold = [(t, -q) for t, q in net.items() if q < 0]
    if len(bought) != 1 or len(sold) != 1:
        raise ValueError("transaction must settle to one effective bought token and one effective sold token")
    return EffectiveTrade(bought[0][0], bought[0][1], sold[0][0], sold[0][1])