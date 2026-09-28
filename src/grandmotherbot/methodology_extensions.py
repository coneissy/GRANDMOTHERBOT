"""Locked methodology extensions for GrandMother.

These extensions sit beside, and never replace, the exact Wu et al. (2025)
paper-replication baseline. They add execution-aware and market-structure
measurements identified during the 2026 research review.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite


@dataclass(frozen=True)
class BlockInterval:
    previous_block_time: datetime
    current_block_time: datetime

    @property
    def seconds(self) -> float:
        value = (self.current_block_time - self.previous_block_time).total_seconds()
        if value < 0:
            raise ValueError("block times must be monotone")
        return value


@dataclass(frozen=True)
class PriceRegime:
    reference_price: float
    previous_price: float
    jump_bps_threshold: float = 50.0

    def classify(self) -> str:
        if self.reference_price <= 0 or self.previous_price <= 0:
            raise ValueError("prices must be positive")
        move_bps = abs(self.reference_price / self.previous_price - 1.0) * 10_000
        return "jump" if move_bps >= self.jump_bps_threshold else "diffusive"


@dataclass(frozen=True)
class CexExecution:
    side: str
    quantity: float
    executable_price: float
    mid_price: float
    fees_usd: float = 0.0
    slippage_usd: float = 0.0

    @property
    def notional_usd(self) -> float:
        if self.quantity <= 0 or self.executable_price <= 0:
            raise ValueError("quantity and executable price must be positive")
        return self.quantity * self.executable_price

    @property
    def execution_cost_usd(self) -> float:
        if self.fees_usd < 0 or self.slippage_usd < 0:
            raise ValueError("execution costs cannot be negative")
        return self.fees_usd + self.slippage_usd

    @property
    def effective_slippage_bps(self) -> float:
        if self.mid_price <= 0:
            raise ValueError("mid price must be positive")
        return abs(self.executable_price / self.mid_price - 1.0) * 10_000


@dataclass(frozen=True)
class AuctionObservation:
    slot: int
    builder: str
    bid_value_wei: int
    winning: bool
    relay: str | None = None
    exclusive_flow: bool = False
    integrated_searcher_flow: bool = False
    latency_ms: float | None = None

    def validate(self) -> None:
        if self.slot < 0:
            raise ValueError("slot must be non-negative")
        if not self.builder:
            raise ValueError("builder is required")
        if self.bid_value_wei < 0:
            raise ValueError("bid value cannot be negative")
        if self.latency_ms is not None and self.latency_ms < 0:
            raise ValueError("latency cannot be negative")


@dataclass(frozen=True)
class ProfitViews:
    paper_pnl_usd: float
    markout_pnl_usd: float
    executable_pnl_usd: float

    def validate(self) -> None:
        values = (self.paper_pnl_usd, self.markout_pnl_usd, self.executable_pnl_usd)
        if not all(isfinite(v) for v in values):
            raise ValueError("profit views must be finite")


def executable_pnl(
    paper_pnl_usd: float,
    cex_execution: CexExecution,
    extra_latency_cost_usd: float = 0.0,
) -> float:
    """Apply measured CEX execution frictions without altering paper PnL."""
    if extra_latency_cost_usd < 0:
        raise ValueError("latency cost cannot be negative")
    result = paper_pnl_usd - cex_execution.execution_cost_usd - extra_latency_cost_usd
    if not isfinite(result):
        raise ValueError("result must be finite")
    return result


def lvr_diagnostic(
    reference_price: float,
    amm_price: float,
    inventory_units: float,
) -> float:
    """Simple adverse-selection diagnostic, kept separate from searcher PnL.

    This is intentionally a diagnostic rather than a full LVR implementation:
    GrandMother must not substitute LVR for MR/EV/PnL.
    """
    if reference_price <= 0 or amm_price <= 0:
        raise ValueError("prices must be positive")
    if inventory_units < 0:
        raise ValueError("inventory cannot be negative")
    return abs(reference_price - amm_price) * inventory_units


METHODOLOGY_LOCK = {
    "paper_baseline": "arXiv:2507.13023v3",
    "extensions": (
        "jump_regime",
        "empirical_block_intervals",
        "cex_executable_pnl",
        "lvr_diagnostic_separate_from_pnl",
        "builder_auction_observation",
        "paper_markout_executable_profit_views",
    ),
    "rule": "extensions never replace the exact paper baseline",
}
