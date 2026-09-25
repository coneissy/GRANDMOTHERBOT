from __future__ import annotations
from decimal import Decimal

def hhi(shares:list[Decimal])->Decimal:
    if any(s<0 for s in shares): raise ValueError("shares must be non-negative")
    total=sum(shares,Decimal("0"))
    if total<=0:return Decimal("0")
    normalized=[s/total for s in shares]
    return sum((s*s for s in normalized),Decimal("0"))

def volume_shares(values:dict[str,Decimal])->dict[str,Decimal]:
    total=sum(values.values(),Decimal("0"))
    return {k:(v/total if total else Decimal("0")) for k,v in values.items()}
