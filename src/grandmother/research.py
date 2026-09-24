from __future__ import annotations

from decimal import Decimal

from .markout import gross_return, HORIZONS
from .models import HedgeObservation

def markout_revenue_series(observation: HedgeObservation) -> dict[Decimal, Decimal]:
    return {p.horizon_s: gross_return(observation, p) * observation.dex_volume_usd for p in observation.markouts}

def persistently_fails_to_cover_base_fees(observation: HedgeObservation, base_fees_usd: Decimal) -> bool:
    series = markout_revenue_series(observation)
    if not set(HORIZONS).issubset(series):
        raise ValueError("complete research markout window is required")
    return all(series[h] < base_fees_usd for h in HORIZONS)

def eligible_for_pnl_estimation(observation: HedgeObservation, base_fees_usd: Decimal) -> bool:
    return not persistently_fails_to_cover_base_fees(observation, base_fees_usd)
