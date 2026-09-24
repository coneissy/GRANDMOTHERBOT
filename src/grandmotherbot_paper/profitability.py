from decimal import Decimal

def estimated_ev(markout_revenue_usd: Decimal, base_fees_usd: Decimal) -> Decimal:
    return markout_revenue_usd - base_fees_usd

def estimated_pnl(ev_usd: Decimal, builder_tips_usd: Decimal) -> Decimal:
    return ev_usd - builder_tips_usd

def profit_margin(ev_usd: Decimal, pnl_usd: Decimal) -> Decimal | None:
    if ev_usd <= 0:
        return None
    return pnl_usd / ev_usd

def inventory_adjustment_like(markout_revenues_usd: list[Decimal], base_fees_usd: Decimal) -> bool:
    if not markout_revenues_usd:
        raise ValueError("markout revenue series is required")
    return all(revenue < base_fees_usd for revenue in markout_revenues_usd)