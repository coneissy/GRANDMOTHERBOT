"""Executable contracts for GrandMother's research and data pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ContractResult:
    name: str
    passed: bool
    evidence: str


def require_nonnegative(value: float, name: str) -> ContractResult:
    return ContractResult(name, value >= 0, f"{name}={value}")


def verify_profit_chain(mr: float, base_fees: float, builder_tips: float, ev: float, pnl: float) -> tuple[ContractResult, ...]:
    """Verify EV/PnL accounting without hiding missing values as zero."""
    if any(v is None for v in (mr, base_fees, builder_tips, ev, pnl)):
        raise ValueError("economic inputs must be explicit")
    return (
        ContractResult("EV_equation", ev == mr - base_fees, f"EV={ev}, MR-base={mr - base_fees}"),
        ContractResult("PnL_equation", pnl == ev - builder_tips, f"PnL={pnl}, EV-tips={ev - builder_tips}"),
        require_nonnegative(base_fees, "base_fees"),
        require_nonnegative(builder_tips, "builder_tips"),
    )


def verify_book_cap(level_count: int, configured_cap: int = 100) -> ContractResult:
    if level_count < 0:
        raise ValueError("level count cannot be negative")
    return ContractResult(
        "book_cap",
        level_count <= configured_cap,
        f"levels={level_count}, cap={configured_cap}",
    )


def verify_timestamp_order(event_time, observation_time) -> ContractResult:
    return ContractResult(
        "timestamp_order",
        observation_time >= event_time,
        f"event={event_time}, observation={observation_time}",
    )


def all_pass(results: Iterable[ContractResult]) -> bool:
    return all(result.passed for result in results)


VERIFICATION_LOCK = {
    "principle": "contract plus executable evidence",
    "fail_closed": True,
    "no_aggregate_score_substitution": True,
}
