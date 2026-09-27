from __future__ import annotations

from dataclasses import dataclass

from .identification import CandidateTransaction, heuristic_flags


@dataclass(frozen=True)
class IdentificationResult:
    """Auditable outcome for the paper's six identification heuristics.

    The flags are evidence about on-chain classification inputs. They do not
    assert that an off-chain CEX hedge was actually observed.
    """

    classification: str
    flags: dict[str, bool]

    @property
    def passed(self) -> bool:
        return self.classification == "candidate_cex_dex"

    @property
    def failed_heuristics(self) -> tuple[str, ...]:
        return tuple(name for name, passed in self.flags.items() if not passed)


def identify_transaction(tx: CandidateTransaction) -> IdentificationResult:
    flags = heuristic_flags(tx)
    classification = (
        "candidate_cex_dex"
        if all(flags.values())
        else "excluded"
    )
    return IdentificationResult(classification=classification, flags=flags)


def identify_transactions(
    transactions: list[CandidateTransaction],
) -> tuple[IdentificationResult, ...]:
    """Apply identification independently to each transaction."""
    return tuple(identify_transaction(tx) for tx in transactions)
