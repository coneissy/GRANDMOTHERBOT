from dataclasses import dataclass
from decimal import Decimal

HORIZONS = tuple(Decimal("-1.0") + Decimal("0.5") * i for i in range(23))

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

def markout_revenue(amount_a: Decimal, amount_b: Decimal, point: MarkoutPoint, cex_taker_fees_usd: Decimal) -> Decimal:
    return amount_a * point.token_a_usdt_mid - amount_b * point.token_b_usdt_mid - cex_taker_fees_usd

def gross_return(observation: TradeObservation, point: MarkoutPoint) -> Decimal:
    if observation.dex_volume_usd <= 0:
        raise ValueError("DEX volume must be positive")
    return markout_revenue(observation.amount_a, observation.amount_b, point, observation.cex_taker_fees_usd) / observation.dex_volume_usd

def median_gr_curve(observations: list[TradeObservation]) -> dict[Decimal, Decimal]:
    if not observations:
        raise ValueError("at least one observation is required")
    curve = {}
    for h in HORIZONS:
        vals = []
        for obs in observations:
            point = next((p for p in obs.markouts if p.horizon_s == h), None)
            if point is not None:
                vals.append(gross_return(obs, point))
        if vals:
            vals.sort()
            n = len(vals)
            curve[h] = vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / Decimal("2")
    return curve

def optimal_horizon(observations: list[TradeObservation]) -> Decimal | None:
    curve = median_gr_curve(observations)
    if not curve:
        return None
    maximum = max(curve.values())
    return max(h for h, value in curve.items() if value == maximum)