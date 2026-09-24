from __future__ import annotations

from .models import CandidateTransaction


def passes_heuristics(tx: CandidateTransaction) -> bool:
    """Implement the paper's six identification heuristics as a strict gate."""
    h1 = tx.is_private
    h2 = tx.first_swap_in_pool_direction
    h3 = (not tx.is_atomic_mev) and (not tx.is_liquidation)
    h4 = not tx.is_ofa_backrun
    h5 = (
        not tx.is_known_router
        and not tx.is_labeled_trading_bot
        and not tx.controls_ens_named_eoa
    )
    h6 = (not tx.contains_erc721_transfer) and tx.final_tokens_cex_listed
    return all((h1, h2, h3, h4, h5, h6))


def heuristic_report(tx: CandidateTransaction) -> dict[str, bool]:
    return {
        "H1_private": tx.is_private,
        "H2_first_swap_pool_direction": tx.first_swap_in_pool_direction,
        "H3_not_atomic_mev_or_liquidation": (not tx.is_atomic_mev)
        and (not tx.is_liquidation),
        "H4_not_ofa_backrun": not tx.is_ofa_backrun,
        "H5_not_known_router_bot_or_ens_eoa": (
            not tx.is_known_router
            and not tx.is_labeled_trading_bot
            and not tx.controls_ens_named_eoa
        ),
        "H6_no_erc721_and_final_pair_cex_listed": (
            not tx.contains_erc721_transfer
        )
        and tx.final_tokens_cex_listed,
    }
