from decimal import Decimal
def interval(values:list[Decimal],q_low:Decimal=Decimal(".05"),q_high:Decimal=Decimal(".95")):
    if not values: raise ValueError("values required")
    x=sorted(values); n=len(x)
    def q(v):
        pos=(n-1)*v; lo=int(pos); hi=min(lo+1,n-1); frac=Decimal(str(pos-lo)); return x[lo]+(x[hi]-x[lo])*frac
    return q(q_low),q(Decimal(".5")),q(q_high)
def mixture_pnl(scenarios:list[tuple[Decimal,Decimal]])->Decimal:
    total=sum((p for p,_ in scenarios),Decimal("0"))
    if total<=0: raise ValueError("scenario probabilities must sum positive")
    return sum((p*v for p,v in scenarios),Decimal("0"))/total
