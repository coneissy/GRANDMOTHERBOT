from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
@dataclass(frozen=True)
class ExecutionOutcome:
    included:bool; succeeded:bool; reverted:bool; stale:bool; outcompeted:bool; censored:bool; inclusion_delay_ms:int|None; hedge_delay_ms:int|None
@dataclass(frozen=True)
class OpportunityDecay:
    horizon_ms:int; profitable_probability:Decimal; expected_pnl_usd:Decimal
def opportunity_half_life(points:list[OpportunityDecay])->int|None:
    if not points:return None
    target=points[0].profitable_probability/Decimal("2")
    return next((p.horizon_ms for p in points if p.profitable_probability<=target),None)
