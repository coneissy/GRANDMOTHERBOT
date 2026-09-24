from collections import defaultdict
from decimal import Decimal

def hhi(values) -> Decimal:
    total=sum((Decimal(str(v)) for v in values), Decimal("0"))
    if total <= 0:
        return Decimal("0")
    return sum((v/total)**2 for v in (Decimal(str(v)) for v in values))

def shares(values):
    total=sum((Decimal(str(v)) for v in values), Decimal("0"))
    if total <= 0:
        return [Decimal("0") for _ in values]
    return [Decimal(str(v))/total for v in values]

def group_sum(rows, key, value):
    out=defaultdict(Decimal)
    for r in rows:
        out[r[key]] += Decimal(str(r[value]))
    return dict(out)

def weekly_hhi(rows, date_key, group_key, value_key):
    grouped=defaultdict(lambda: defaultdict(Decimal))
    for r in rows:
        grouped[r[date_key]][r[group_key]] += Decimal(str(r[value_key]))
    result={}
    for period, groups in grouped.items():
        result[period]=hhi(groups.values())
    return result
