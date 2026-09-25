from grandmotherbot.research_alignment import (
    CURATED_TRANSACTIONS,
    DUNE_QUERY_ID,
    IDENTIFIED_ARBITRAGES,
    INVENTORY_ADJUSTMENTS,
    MISSING_TARDIS_PRICES,
)


def test_paper_reconciliation_targets_are_frozen():
    assert DUNE_QUERY_ID == 4931834
    assert CURATED_TRANSACTIONS == 8_723_233
    assert MISSING_TARDIS_PRICES == 163_148
    assert INVENTORY_ADJUSTMENTS == 683_539
    assert IDENTIFIED_ARBITRAGES == 7_203_560


def test_reconciliation_stages_are_distinct():
    assert CURATED_TRANSACTIONS > MISSING_TARDIS_PRICES
    assert CURATED_TRANSACTIONS > INVENTORY_ADJUSTMENTS
    assert IDENTIFIED_ARBITRAGES < CURATED_TRANSACTIONS
