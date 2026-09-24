from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class LiquidityPoint:
    size_usd: Decimal
    dex_execution_value_usd: Decimal
    cex_hedge_value_usd: Decimal
    fees_and_gas_usd: Decimal
    builder_payment_usd: Decimal
    execution_risk_usd: Decimal = Decimal("0")

    @property
    def expected_pnl_usd(self) -> Decimal:
        return (
            self.dex_execution_value_usd
            - self.cex_hedge_value_usd
            - self.fees_and_gas_usd
            - self.builder_payment_usd
            - self.execution_risk_usd
        )


def choose_size(points: list[LiquidityPoint]) -> LiquidityPoint:
    if not points:
        raise ValueError("no liquidity points supplied")
    return max(points, key=lambda p: p.expected_pnl_usd)
