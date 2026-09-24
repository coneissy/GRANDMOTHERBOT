from dataclasses import dataclass
from .constants import MANUAL_EXCLUDED_ADDRESSES

@dataclass(frozen=True)
class CandidateTransaction:
    observed_public_mempool: bool
    first_swap_in_pool_direction: bool
    atomic_mev: bool
    liquidation: bool
    ofa_backrun: bool
    known_router: bool
    labeled_trading_bot: bool
    ens_named_eoa_controller: bool
    erc721_transfer: bool
    final_pair_major_cex_listed: bool
    from_address: str | None = None

    @property
    def private(self) -> bool:
        return not self.observed_public_mempool

    @property
    def manually_excluded(self) -> bool:
        return (self.from_address or "").lower() in MANUAL_EXCLUDED_ADDRESSES

def heuristic_flags(tx: CandidateTransaction) -> dict[str, bool]:
    return {
        "H1_private": tx.private,
        "H2_first_swap_pool_direction": tx.first_swap_in_pool_direction,
        "H3_not_atomic_mev_or_liquidation": not tx.atomic_mev and not tx.liquidation,
        "H4_not_ofa_backrun": not tx.ofa_backrun,
        "H5_not_known_router_bot_or_ens_eoa": (
            not tx.known_router
            and not tx.labeled_trading_bot
            and not tx.ens_named_eoa_controller
        ),
        "H6_no_erc721_and_final_pair_major_cex_listed": (
            not tx.erc721_transfer and tx.final_pair_major_cex_listed
        ),
        "appendix_manual_exclusion": not tx.manually_excluded,
    }

def passes_all_heuristics(tx: CandidateTransaction) -> bool:
    flags = heuristic_flags(tx)
    return all(flags[name] for name in flags)

def classify_transaction(tx: CandidateTransaction) -> str:
    if passes_all_heuristics(tx):
        return "candidate_cex_dex"
    return "excluded"
