from decimal import Decimal
def inventory_carry_cost(notional_usd:Decimal,duration_seconds:Decimal,annual_rate:Decimal,risk_bps:Decimal=Decimal("0"))->Decimal:
    if notional_usd<0 or duration_seconds<0: raise ValueError("notional and duration must be non-negative")
    return notional_usd*annual_rate*duration_seconds/Decimal("31536000")+notional_usd*risk_bps/Decimal("10000")
