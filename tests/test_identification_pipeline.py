from grandmotherbot_paper.identification import CandidateTransaction
from grandmotherbot_paper.identification_pipeline import (
    identify_transaction,
    identify_transactions,
)


def test_identification_result_exposes_failed_heuristics():
    tx = CandidateTransaction(
        observed_public_mempool=True,
        first_swap_in_pool_direction=True,
        atomic_mev=False,
        liquidation=False,
        ofa_backrun=False,
        known_router=False,
        labeled_trading_bot=False,
        ens_named_eoa_controller=False,
        erc721_transfer=False,
        final_pair_major_cex_listed=True,
    )
    result = identify_transaction(tx)
    assert result.classification == "excluded"
    assert result.failed_heuristics == ("H1_private",)


def test_identification_pipeline_preserves_all_six_heuristics():
    tx = CandidateTransaction(
        False, True, False, False, False,
        False, False, False, False, True,
    )
    result = identify_transaction(tx)
    assert result.passed
    assert result.failed_heuristics == ()
    assert set(result.flags) == {
        "H1_private",
        "H2_first_swap_pool_direction",
        "H3_not_atomic_mev_or_liquidation",
        "H4_not_ofa_backrun",
        "H5_not_known_router_bot_or_ens_eoa",
        "H6_no_erc721_and_final_pair_major_cex_listed",
        "appendix_manual_exclusion",
    }


def test_batch_identification_is_order_preserving():
    good = CandidateTransaction(
        False, True, False, False, False,
        False, False, False, False, True,
    )
    public = CandidateTransaction(
        True, True, False, False, False,
        False, False, False, False, True,
    )
    results = identify_transactions([good, public])
    assert [r.classification for r in results] == [
        "candidate_cex_dex",
        "excluded",
    ]
