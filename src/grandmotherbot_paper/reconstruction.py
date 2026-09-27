from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Swap:
    token_in: str
    token_out: str
    amount_in: Decimal
    amount_out: Decimal
    log_index: int = 0


@dataclass(frozen=True)
class EffectiveTrade:
    token_bought: str
    amount_bought: Decimal
    token_sold: str
    amount_sold: Decimal


def reconstruct_effective_trade(swaps: tuple[Swap, ...]) -> EffectiveTrade:
    """Collapse a transaction's swap path to its net sold/bought pair."""
    if not swaps:
        raise ValueError("at least one swap is required")
    for swap in swaps:
        if swap.amount_in <= 0 or swap.amount_out <= 0:
            raise ValueError("swap amounts must be positive")
        if not swap.token_in or not swap.token_out:
            raise ValueError("swap tokens must be non-empty")
        if swap.token_in == swap.token_out:
            raise ValueError("swap cannot have identical input and output tokens")

    net: defaultdict[str, Decimal] = defaultdict(Decimal)
    for swap in sorted(swaps, key=lambda item: item.log_index):
        net[swap.token_in] -= swap.amount_in
        net[swap.token_out] += swap.amount_out

    bought = [(token, quantity) for token, quantity in net.items() if quantity > 0]
    sold = [(token, -quantity) for token, quantity in net.items() if quantity < 0]
    if len(bought) != 1 or len(sold) != 1:
        raise ValueError(
            "transaction does not reduce to one net bought and one net sold token"
        )

    return EffectiveTrade(
        token_bought=bought[0][0],
        amount_bought=bought[0][1],
        token_sold=sold[0][0],
        amount_sold=sold[0][1],
    )
