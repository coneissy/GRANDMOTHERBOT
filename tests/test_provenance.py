from grandmotherbot_extension.provenance import source_run


def test_source_run_requires_accounted_rows():
    run = source_run(
        source="dune",
        query_id="4931834",
        requested_from="2025-01-01T00:00:00Z",
        requested_to="2025-01-02T00:00:00Z",
        rows_received=10,
        rows_accepted=8,
        rows_rejected=2,
    )
    assert run.source == "dune"
    assert run.query_id == "4931834"
    assert run.rows_accepted + run.rows_rejected == run.rows_received
    assert run.schema_version == "1"


def test_source_run_rejects_unaccounted_rows():
    import pytest

    with pytest.raises(ValueError):
        source_run(
            source="tardis",
            requested_from="2025-01-01T00:00:00Z",
            requested_to="2025-01-01T00:01:00Z",
            rows_received=10,
            rows_accepted=9,
            rows_rejected=0,
        )
