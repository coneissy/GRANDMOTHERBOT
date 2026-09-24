from dataclasses import dataclass
from decimal import Decimal

from .constants import HORIZONS


@dataclass(frozen=True)
class MarkoutPoint:
    horizon_s: Decimal
    token_a_usdt_mid: Decimal
    token_b_usdt_mid: Decimal


@dataclass(frozen=True)
class TradeObservation:
    amount_a: Decimal
    amount_b: Decimal
    dex_volume_usd: Decimal
    cex_taker_fees_usd: Decimal
    markouts: tuple[MarkoutPoint, ...]
    base_fees_usd: Decimal = Decimal("0")


def markout_revenue(
    amount_a: Decimal,
    amount_b: Decimal,
    point: MarkoutPoint,
    cex_taker_fees_usd: Decimal,
) -> Decimal:
    return (
        amount_a * point.token_a_usdt_mid
        - amount_b * point.token_b_usdt_mid
        - cex_taker_fees_usd
    )


def gross_return(observation: TradeObservation, point: MarkoutPoint) -> Decimal:
    if observation.dex_volume_usd <= 0:
        raise ValueError("DEX volume must be positive")
    return markout_revenue(
        observation.amount_a,
        observation.amount_b,
        point,
        observation.cex_taker_fees_usd,
    ) / observation.dex_volume_usd


def median(values: list[Decimal]) -> Decimal:
    values = sorted(values)
    n = len(values)
    if n == 0:
        raise ValueError("cannot take median of an empty sequence")
    return values[n // 2] if n % 2 else (values[n // 2 - 1] + values[n // 2]) / Decimal("2")


def median_gr_curve(observations: list[TradeObservation]) -> dict[Decimal, Decimal]:
    if not observations:
        raise ValueError("at least one trade observation is required")
    curve: dict[Decimal, Decimal] = {}
    for horizon in HORIZONS:
        values = []
        for observation in observations:
            point = next(
                (p for p in observation.markouts if p.horizon_s == horizon),
                None,
            )
            if point is not None:
                values.append(gross_return(observation, point))
        if values:
            curve[horizon] = median(values)
    return curve


def optimal_horizon(observations: list[TradeObservation]) -> Decimal | None:
    curve = median_gr_curve(observations)
    if set(curve) != set(HORIZONS):
        return None
    maximum = max(curve.values())
    return max(
        horizon for horizon, value in curve.items() if value == maximum
    )


def complete_markout_window(observation: TradeObservation) -> bool:
    return all(
        any(point.horizon_s == horizon for point in observation.markouts)
        for horizon in HORIZONS
    )


def inventory_adjustment_like_observation(
    observation: TradeObservation,
) -> bool:
    """Section 4.1 exclusion: MR stays below base fees across the full window."""
    if not complete_markout_window(observation):
        return False
    revenues = [
        markout_revenue(
            observation.amount_a,
            observation.amount_b,
            point,
            observation.cex_taker_fees_usd,
        )
        for horizon in HORIZONS
        for point in observation.markouts
        if point.horizon_s == horizon
    ]
    return len(revenues) == len(HORIZONS) and all(
        revenue < observation.base_fees_usd for revenue in revenues
    )
