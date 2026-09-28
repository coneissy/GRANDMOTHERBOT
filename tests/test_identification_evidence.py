import pytest

from grandmotherbot_extension.identification_evidence import (
    REQUIRED_EVIDENCE,
    build_identification_evidence,
    evaluate_identification,
)


def values(**overrides):
    base = {name: False for name in REQUIRED_EVIDENCE}
    base["first_swap_in_pool_direction"] = True
    base["final_pair_major_cex_listed"] = True
    base.update(overrides)
    return base


def sources():
    return {name: f"source:{name}" for name in REQUIRED_EVIDENCE}


def test_builds_auditable_h1_h6_evidence():
    evidence = build_identification_evidence(
        values(), sources=sources(), from_address="0xabc"
    )
    result = evaluate_identification(evidence)

    assert result["classification"] == "candidate_cex_dex"
    assert all(result["flags"][name] for name in result["flags"])
    assert result["evidence_sources"]["first_swap_in_pool_direction"] == (
        "source:first_swap_in_pool_direction"
    )


def test_missing_evidence_is_rejected():
    data = values()
    del data["atomic_mev"]
    with pytest.raises(ValueError, match="atomic_mev"):
        build_identification_evidence(data, sources=sources())


def test_missing_provenance_is_rejected():
    provenance = sources()
    del provenance["ofa_backrun"]
    with pytest.raises(ValueError, match="ofa_backrun"):
        build_identification_evidence(values(), sources=provenance)


def test_boolean_strings_are_supported_but_ambiguous_values_are_rejected():
    data = values()
    data["known_router"] = "false"
    evidence = build_identification_evidence(data, sources=sources())
    assert evaluate_identification(evidence)["classification"] == "candidate_cex_dex"

    data["known_router"] = "unknown"
    with pytest.raises(ValueError, match="known_router"):
        build_identification_evidence(data, sources=sources())
