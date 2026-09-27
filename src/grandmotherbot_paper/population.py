from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .identification_pipeline import IdentificationResult

# Project reconciliation target supplied for the GrandMother empirical dataset.
# This is a validation target, not a claim that the paper defines this number.
CANDIDATE_POPULATION_TARGET = 8_723_233


@dataclass(frozen=True)
class PopulationReconciliation:
    """Auditable reconciliation of an ingested population against its target."""

    total_input: int
    candidate_count: int
    excluded_count: int
    target_count: int
    delta_to_target: int

    @property
    def matches_target(self) -> bool:
        return self.delta_to_target == 0


def reconcile_candidate_population(
    total_input: int,
    candidate_count: int,
    *,
    target_count: int = CANDIDATE_POPULATION_TARGET,
) -> PopulationReconciliation:
    """Reconcile classifier output without changing classification semantics."""
    for name, value in (
        ("total_input", total_input),
        ("candidate_count", candidate_count),
        ("target_count", target_count),
    ):
        if value < 0:
            raise ValueError(f"{name} must be non-negative")
    if candidate_count > total_input:
        raise ValueError("candidate_count cannot exceed total_input")

    return PopulationReconciliation(
        total_input=total_input,
        candidate_count=candidate_count,
        excluded_count=total_input - candidate_count,
        target_count=target_count,
        delta_to_target=candidate_count - target_count,
    )


def reconcile_identification_results(
    results: Iterable[IdentificationResult],
    *,
    target_count: int = CANDIDATE_POPULATION_TARGET,
) -> PopulationReconciliation:
    """Reconcile H1-H6 results while preserving every result for auditability."""
    materialized = tuple(results)
    candidate_count = sum(result.passed for result in materialized)
    return reconcile_candidate_population(
        len(materialized),
        candidate_count,
        target_count=target_count,
    )
