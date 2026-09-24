from __future__ import annotations

from decimal import Decimal
from statistics import median

from .models import HedgeObservation, MarkoutPoint, SearcherPattern

HORIZONS = tuple(Decimal("-1.0") + Decimal("0.5") * i for i in range(23))


def markout_revenue(
    amount_a: Decimal,
    amount_b: Decimal,
    point: MarkoutPoint,
    cex_taker_fee_usd: Decimal,
) -> Decimal:
    return (
        amount_a * point.token_a_usdt_mid
        - amount_b * point.token_b_usdt_mid
        - cex_taker_fee_usd
    )


def gross_return(observation: HedgeObservation, point: MarkoutPoint) -> Decimal:
    return markout_revenue(
        observation.amount_a,
        observation.amount_b,
        point,
        observation.cex_taker_fee_usd,
    ) / observation.dex_volume_usd


def median_gr_curve(observations: list[HedgeObservation]) -> dict[Decimal, Decimal]:
    if not observations:
        raise ValueError("at least one observation is required")

    curve: dict[Decimal, Decimal] = {}
    for h in HORIZONS:
        vals = []
        for obs in observations:
            pts = [p for p in obs.markouts if p.horizon_s == h]
            if pts:
                vals.append(gross_return(obs, pts[0]))
        if vals:
            curve[h] = Decimal(str(median([float(v) for v in vals])))
    return curve


def optimal_horizon(observations: list[HedgeObservation]) -> Decimal | None:
    """t* = argmax_t median_i GR_i(t), choosing the largest tied horizon."""
    curve = median_gr_curve(observations)
    if not curve:
        return None
    best = max(curve.values())
    return max(h for h, v in curve.items() if v == best)


def classify_pattern(observations: list[HedgeObservation]) -> SearcherPattern:
    curve = median_gr_curve(observations)
    if not curve:
        return SearcherPattern.UNKNOWN

    peak_h = max(curve, key=lambda h: curve[h])
    peak = curve[peak_h]

    post = [v for h, v in sorted(curve.items()) if h > peak_h]
    if not post:
        return SearcherPattern.PATTERN_3

    max_tail = max(post)
    end = post[-1]
    if abs(float(peak - end)) < 0.01 * max(1.0, abs(float(peak))):
        return SearcherPattern.PATTERN_3

    first_3s = [v for h, v in sorted(curve.items()) if peak_h < h <= peak_h + 3]
    if first_3s:
        decay = peak - min(first_3s)
        if decay > Decimal("0.40") * max(abs(peak), Decimal("0.00000001")):
            return SearcherPattern.PATTERN_2
    return SearcherPattern.PATTERN_1
