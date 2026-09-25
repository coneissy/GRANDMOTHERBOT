from __future__ import annotations
from decimal import Decimal
from dataclasses import dataclass
@dataclass(frozen=True)
class AMMQuote:
    amount_in:Decimal; amount_out:Decimal; fee_usd:Decimal; price_impact_usd:Decimal; gas_usd:Decimal=Decimal("0")
class ConstantProductPool:
    def __init__(self,reserve_in:Decimal,reserve_out:Decimal,fee_bps:Decimal):
        if reserve_in<=0 or reserve_out<=0: raise ValueError("reserves must be positive")
        self.reserve_in=reserve_in; self.reserve_out=reserve_out; self.fee_bps=fee_bps
    def quote(self,amount_in:Decimal,gas_usd:Decimal=Decimal("0"))->AMMQuote:
        if amount_in<=0: raise ValueError("amount_in must be positive")
        fee=amount_in*self.fee_bps/Decimal("10000"); effective=amount_in-fee; out=self.reserve_out*effective/(self.reserve_in+effective)
        ideal=effective*(self.reserve_out/self.reserve_in); return AMMQuote(amount_in,out,fee,ideal-out,gas_usd)
