from __future__ import annotations

"""Auditable G3 candidate-population funnel for PAPER_REPLICATION.

G3 measures the frozen H1-H6 classifier step-by-step. It never changes the
identification rules and never invents missing evidence. Empirical PASS requires
real captured Dune rows; fixture results are structural tests only.
"""

from dataclasses import dataclass
from typing import Any

from grandmotherbot_paper.constants import (
    PAPER_END_BLOCK,
    PAPER_START_BLOCK,
    PAPER_START_DATE,
    PAPER_END_DATE,
)
from grandmotherbot_paper.identification import CandidateTransaction, heuristic_flags

H1_H6 = (
    "H1_private",
    "H2_first_swap_pool_direction",
    "H3_not_atomic_mev_or_liquidation",
    "H4_not_ofa_backrun",
    "H5_not_known_router_bot_or_ens_eoa",
    "H6_no_erc721_and_final_pair_major_cex_listed",
)

ALIASES = {
    "tx_hash": ("tx_hash", "transaction_hash"),
    "block_number": ("block_number",),
    "slot_time": ("slot_time", "block_time"),
    "from_address": ("from_address", "tx_from"),
    "observed_public_mempool": ("observed_public_mempool",),
    "first_swap_in_pool_direction": ("first_swap_in_pool_direction",),
    "atomic_mev": ("atomic_mev",),
    "liquidation": ("liquidation",),
    "ofa_backrun": ("ofa_backrun",),
    "known_router": ("known_router",),
    "labeled_trading_bot": ("labeled_trading_bot",),
    "ens_named_eoa_controller": ("ens_named_eoa_controller",),
    "erc721_transfer": ("erc721_transfer",),
    "final_pair_major_cex_listed": ("final_pair_major_cex_listed",),
}

BOOL_FIELDS = set(ALIASES) - {"tx_hash", "block_number", "slot_time", "from_address"}


@dataclass(frozen=True)
class G3Report:
    source_rows: int
    unique_tx_hashes: int
    duplicate_rows: int
    in_block_range: int
    in_date_range: int
    funnel_counts: dict[str, int]
    exclusion_reasons: dict[str, int]
    manual_exclusions: int
    final_candidates: int
    expected_candidate_population: int | None = None

    @property
    def expected_delta(self) -> int | None:
        if self.expected_candidate_population is None:
            return None
        return self.final_candidates - self.expected_candidate_population


def _value(row: dict[str, Any], name: str) -> Any:
    for key in ALIASES[name]:
        if key in row:
            return row[key]
    raise ValueError(f"G3 row missing required field: {name}")


def _bool(row: dict[str, Any], name: str) -> bool:
    value = _value(row, name)
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str) and value.strip().lower() in {"true", "false"}:
        return value.strip().lower() == "true"
    raise ValueError(f"{name}: expected unambiguous boolean, got {value!r}")


def _candidate(row: dict[str, Any]) -> CandidateTransaction:
    return CandidateTransaction(
        observed_public_mempool=_bool(row, "observed_public_mempool"),
        first_swap_in_pool_direction=_bool(row, "first_swap_in_pool_direction"),
        atomic_mev=_bool(row, "atomic_mev"),
        liquidation=_bool(row, "liquidation"),
        ofa_backrun=_bool(row, "ofa_backrun"),
        known_router=_bool(row, "known_router"),
        labeled_trading_bot=_bool(row, "labeled_trading_bot"),
        ens_named_eoa_controller=_bool(row, "ens_named_eoa_controller"),
        erc721_transfer=_bool(row, "erc721_transfer"),
        final_pair_major_cex_listed=_bool(row, "final_pair_major_cex_listed"),
        from_address=str(_value(row, "from_address")).lower(),
    )


def _in_date_range(value: Any) -> bool:
    if value is None:
        return False
    return str(value)[:10] >= PAPER_START_DATE and str(value)[:10] <= PAPER_END_DATE


def build_g3_report(
    rows: list[dict[str, Any]],
    *,
    expected_candidate_population: int | None = None,
) -> G3Report:
    seen: set[str] = set()
    unique_rows: list[dict[str, Any]] = []
    duplicate_rows = 0

    for row in rows:
        tx_hash = str(_value(row, "tx_hash")).lower()
        if tx_hash in seen:
            duplicate_rows += 1
            continue
        seen.add(tx_hash)
        unique_rows.append(row)

    in_block = [
        row for row in unique_rows
        if PAPER_START_BLOCK <= int(_value(row, "block_number")) <= PAPER_END_BLOCK
    ]
    in_date = [row for row in in_block if _in_date_range(_value(row, "slot_time"))]

    funnel_counts = {"source_unique": len(in_date)}
    exclusion_reasons: dict[str, int] = {}
    current = in_date
    manual_exclusions = 0

    for name in H1_H6:
        kept = []
        rejected = 0
        for row in current:
            flags = heuristic_flags(_candidate(row))
            if flags[name]:
                kept.append(row)
            else:
                rejected += 1
        funnel_counts[name] = len(kept)
        exclusion_reasons[name] = rejected
        current = kept

    for row in current:
        if not heuristic_flags(_candidate(row))["appendix_manual_exclusion"]:
            manual_exclusions += 1
    final_candidates = len(current) - manual_exclusions

    return G3Report(
        source_rows=len(rows),
        unique_tx_hashes=len(seen),
        duplicate_rows=duplicate_rows,
        in_block_range=len(in_block),
        in_date_range=len(in_date),
        funnel_counts=funnel_counts,
        exclusion_reasons=exclusion_reasons,
        manual_exclusions=manual_exclusions,
        final_candidates=final_candidates,
        expected_candidate_population=expected_candidate_population,
    )
