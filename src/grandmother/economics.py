from __future__ import annotations

from decimal import Decimal
from dataclasses import dataclass


@dataclass(frozen=True)
class TradeEconomics:
    markout_revenue_usd: Decimal
    base_fees_usd: Decimal
    builder_tips_usd: Decimal

    @property
    def estimated_ev_usd(self) -> Decimal:
        return self.markout_revenue_usd - self.base_fees_usd

    @property
    def estimated_pnl_usd(self) -> Decimal:
        return self.estimated_ev_usd - self.builder_tips_usd

    @property
    def profit_margin(self) -> Decimal | None:
        ev = self.estimated_ev_usd
        if ev <= 0:
            return None
        return self.estimated_pnl_usd / ev


def subsidized_block(builder_profit_usd: Decimal, aggregated_profit_usd: Decimal) -> bool:
    """Paper definition: both builder and aggregated profits must be negative."""
    return builder_profit_usd < 0 and aggregated_profit_usd < 0
