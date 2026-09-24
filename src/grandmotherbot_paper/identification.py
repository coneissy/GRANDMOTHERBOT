from dataclasses import dataclass

@dataclass(frozen=True)
class Candidate:
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

    @property
    def private(self) -> bool:
        return not self.observed_public_mempool

def heuristic_flags(tx: Candidate) -> dict[str, bool]:
    return {
        "H1": tx.private,
        "H2": tx.first_swap_in_pool_direction,
        "H3": not tx.atomic_mev and not tx.liquidation,
        "H4": not tx.ofa_backrun,
        "H5": not tx.known_router and not tx.labeled_trading_bot and not tx.ens_named_eoa_controller,
        "H6": not tx.erc721_transfer and tx.final_pair_major_cex_listed,
    }

def passes_all_heuristics(tx: Candidate) -> bool:
    return all(heuristic_flags(tx).values())