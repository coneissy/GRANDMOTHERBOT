from grandmotherbot_paper.reconciliation import (
    empirical_reproduction_status,
    validate_reference_tables,
)


def test_reference_tables_reconcile():
    validate_reference_tables()


def test_empirical_reproduction_is_not_claimed_without_raw_inputs():
    status = empirical_reproduction_status()
    assert status.reference_integrity is True
    assert status.raw_dataset_available is False
    assert status.empirical_reproduction is False
