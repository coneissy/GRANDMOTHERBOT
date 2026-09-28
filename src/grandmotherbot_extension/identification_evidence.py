from __future__ import annotations

"""Explicit evidence layer for the frozen PAPER_REPLICATION H1-H6 rules.

This module does not infer missing evidence. Each heuristic is backed by a
named evidence field and its provenance source. Missing or ambiguous evidence
is rejected so the Dune bridge cannot silently turn an incomplete source row
into a paper candidate.
"""

from dataclasses import dataclass
from typing import Any

from grandmotherbot_paper.identification import CandidateTransaction, classify_transaction, heuristic_flags


REQUIRED_EVIDENCE = (
    "observed_public_mempool",
    "first_swap_in_pool_direction",
    "atomic_mev",
    "liquidation",
    "ofa_backrun",
    "known_router",
    "labeled_trading_bot",
    "ens_named_eoa_controller",
    "erc721_transfer",
    "final_pair_major_cex_listed",
)


@dataclass(frozen=True)
class EvidenceValue:
    value: bool
    source: str


@dataclass(frozen=True)
class IdentificationEvidence:
    observed_public_mempool: EvidenceValue
    first_swap_in_pool_direction: EvidenceValue
    atomic_mev: EvidenceValue
    liquidation: EvidenceValue
    ofa_backrun: EvidenceValue
    known_router: EvidenceValue
    labeled_trading_bot: EvidenceValue
    ens_named_eoa_controller: EvidenceValue
    erc721_transfer: EvidenceValue
    final_pair_major_cex_listed: EvidenceValue
    from_address: str | None = None

    def as_candidate(self) -> CandidateTransaction:
        return CandidateTransaction(
            observed_public_mempool=self.observed_public_mempool.value,
            first_swap_in_pool_direction=self.first_swap_in_pool_direction.value,
            atomic_mev=self.atomic_mev.value,
            liquidation=self.liquidation.value,
            ofa_backrun=self.ofa_backrun.value,
            known_router=self.known_router.value,
            labeled_trading_bot=self.labeled_trading_bot.value,
            ens_named_eoa_controller=self.ens_named_eoa_controller.value,
            erc721_transfer=self.erc721_transfer.value,
            final_pair_major_cex_listed=self.final_pair_major_cex_listed.value,
            from_address=self.from_address,
        )

    def sources(self) -> dict[str, str]:
        return {
            name: getattr(self, name).source
            for name in REQUIRED_EVIDENCE
        }


def _coerce_bool(value: Any, field: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "false"}:
            return normalized == "true"
    raise ValueError(f"{field}: evidence must be an unambiguous boolean, got {value!r}")


def build_identification_evidence(
    values: dict[str, Any],
    *,
    sources: dict[str, str],
    from_address: str | None = None,
) -> IdentificationEvidence:
    missing = [name for name in REQUIRED_EVIDENCE if name not in values]
    if missing:
        raise ValueError(
            "missing H1-H6 evidence: " + ", ".join(missing)
        )

    missing_sources = [
        name for name in REQUIRED_EVIDENCE
        if name not in sources or not str(sources[name]).strip()
    ]
    if missing_sources:
        raise ValueError(
            "missing provenance for H1-H6 evidence: "
            + ", ".join(missing_sources)
        )

    return IdentificationEvidence(
        **{
            name: EvidenceValue(
                _coerce_bool(values[name], name),
                str(sources[name]),
            )
            for name in REQUIRED_EVIDENCE
        },
        from_address=from_address,
    )


def evaluate_identification(
    evidence: IdentificationEvidence,
) -> dict[str, Any]:
    """Evaluate the frozen classifier and return an auditable H1-H6 record."""
    candidate = evidence.as_candidate()
    flags = heuristic_flags(candidate)
    return {
        "classification": classify_transaction(candidate),
        "flags": flags,
        "evidence_sources": evidence.sources(),
    }
