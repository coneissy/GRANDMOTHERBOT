from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ExecutionDecision:
    execute: bool
    expected_pnl_usd: Decimal
    reason: str


class PaperExecutor:
    """DEX-first, confirmation-gated CEX hedge boundary.

    This class never submits a live transaction. It models the sequencing
    required by the paper: DEX execution first, then hedge after confirmation.
    """

    def decide(self, expected_pnl_usd: Decimal, min_pnl_usd: Decimal) -> ExecutionDecision:
        if expected_pnl_usd >= min_pnl_usd:
            return ExecutionDecision(True, expected_pnl_usd, "paper_execution_approved")
        return ExecutionDecision(False, expected_pnl_usd, "expected_pnl_below_threshold")

    def hedge_allowed(self, dex_confirmed: bool) -> bool:
        return dex_confirmed
