from __future__ import annotations
from decimal import Decimal

def paper_markout(amount_a:Decimal,amount_b:Decimal,price_a:Decimal,price_b:Decimal,cex_fee_usd:Decimal)->Decimal:return amount_a*price_a-amount_b*price_b-cex_fee_usd
def executable_markout(proceeds_usd:Decimal,hedge_cost_usd:Decimal,fees_usd:Decimal)->Decimal:return proceeds_usd-hedge_cost_usd-fees_usd
def gross_return(revenue_usd:Decimal,volume_usd:Decimal)->Decimal:
    if volume_usd<=0:raise ValueError("volume must be positive")
    return revenue_usd/volume_usd
