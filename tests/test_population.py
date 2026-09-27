import pytest

from grandmotherbot_paper.identification_pipeline import IdentificationResult
from grandmotherbot_paper.population import (
    CANDIDATE_POPULATION_TARGET,
    reconcile_candidate_population,
    reconcile_identification_results,
)


def test_candidate_population_reconciles_to_target():
    result = reconcile_candidate_population(
        total_input=10,
        candidate_count=CANDIDATE_POPULATION_TARGET,
        target_count=CANDIDATE_POPULATION_TARGET,
    )
    assert result.matches_target
    assert result.excluded_count == 10 - CANDIDATE_POPULATION_TARGET
    assert result.delta_to_target == 0


def test_candidate_population_reports_delta_without_mutating_count():
    result = reconcile_candidate_population(
        total_input=20,
        candidate_count=7,
        target_count=10,
    )
    assert not result.matches_target
    assert result.candidate_count == 7
    assert result.excluded_count == 13
    assert result.delta_to_target == -3


def test_identification_results_are_reconciled_after_h1_h6():
    results = (
        IdentificationResult(
            classification="candidate_cex_dex",
            flags={"H1_private": True},
        ),
        IdentificationResult(
            classification="excluded",
            flags={"H1_private": False},
        ),
        IdentificationResult(
            classification="candidate_cex_dex",
            flags={"H1_private": True},
        ),
    )
    result = reconcile_identification_results(results, target_count=2)
    assert result.total_input == 3
    assert result.candidate_count == 2
    assert result.excluded_count == 1
    assert result.matches_target


@pytest.mark.parametrize(
    "total_input,candidate_count",
    [(-1, 0), (1, -1), (1, 2)],
)
def test_candidate_population_rejects_invalid_counts(total_input, candidate_count):
    with pytest.raises(ValueError):
        reconcile_candidate_population(total_input, candidate_count)
