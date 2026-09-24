from __future__ import annotations

import pandas as pd

from .constants import HORIZONS, KNOWN_PATTERN_BY_SEARCHER
from .markout import complete_markout_window, inventory_adjustment_like_observation
from .reproduction import build_observations

PATTERN_3_SEARCHERS = frozenset(
    label
    for label, (_, pattern) in KNOWN_PATTERN_BY_SEARCHER.items()
    if pattern == 3
)

EXPECTED_DETECTED = 8_723_233
EXPECTED_MISSING_TARDIS = 163_148
EXPECTED_INVENTORY_ADJUSTMENT = 683_539
EXPECTED_PATTERN_3 = 239_933
EXPECTED_UNLABELED = 433_053
EXPECTED_FINAL_ARBITRAGES = 7_203_560


def missing_tardis_hashes(
    transactions: pd.DataFrame,
    markouts: pd.DataFrame,
) -> set[str]:
    required = {"tx_hash", "horizon_s", "token_a_usdt_mid", "token_b_usdt_mid"}
    missing = required - set(markouts.columns)
    if missing:
        raise ValueError(
            "markouts missing Appendix H fields: " + ", ".join(sorted(missing))
        )

    tx_hashes = set(transactions.tx_hash.astype(str))
    work = markouts.copy()
    work["tx_hash"] = work.tx_hash.astype(str)
    work["horizon_s"] = pd.to_numeric(work.horizon_s, errors="coerce")
    expected_horizons = {float(horizon) for horizon in HORIZONS}

    missing_hashes = set()
    for tx_hash in tx_hashes:
        group = work[work.tx_hash == tx_hash]
        horizons = set(group.horizon_s.dropna().astype(float))
        if horizons != expected_horizons:
            missing_hashes.add(tx_hash)
            continue
        if group[["token_a_usdt_mid", "token_b_usdt_mid"]].isna().any().any():
            missing_hashes.add(tx_hash)
    return missing_hashes


def reconcile_appendix_h(
    transactions: pd.DataFrame,
    markouts: pd.DataFrame,
) -> pd.DataFrame:
    detected = transactions.copy()
    detected["tx_hash"] = detected.tx_hash.astype(str)

    missing = missing_tardis_hashes(detected, markouts)
    remaining = detected[~detected.tx_hash.isin(missing)].copy()

    observations = build_observations(markouts)
    remaining_hashes = set(remaining.tx_hash)
    inventory = {
        tx_hash
        for tx_hash, observation in observations.items()
        if tx_hash in remaining_hashes
        and complete_markout_window(observation)
        and inventory_adjustment_like_observation(observation)
    }
    remaining = remaining[~remaining.tx_hash.isin(inventory)].copy()

    labels = (
        remaining["searcher_label"].astype(str)
        if "searcher_label" in remaining
        else pd.Series("", index=remaining.index)
    )
    pattern3 = set(
        remaining.loc[labels.isin(PATTERN_3_SEARCHERS), "tx_hash"]
    )
    labeled = set(KNOWN_PATTERN_BY_SEARCHER)
    unlabeled = set(
        remaining.loc[~labels.isin(labeled), "tx_hash"]
    )
    final = remaining[~remaining.tx_hash.isin(pattern3 | unlabeled)].copy()

    stages = [
        ("detected_by_heuristics", len(detected), EXPECTED_DETECTED),
        ("removed_missing_tardis", len(missing), EXPECTED_MISSING_TARDIS),
        (
            "removed_inventory_adjustment",
            len(inventory),
            EXPECTED_INVENTORY_ADJUSTMENT,
        ),
        ("removed_pattern_3", len(pattern3), EXPECTED_PATTERN_3),
        ("removed_unlabeled", len(unlabeled), EXPECTED_UNLABELED),
        ("remaining_arbitrages", len(final), EXPECTED_FINAL_ARBITRAGES),
    ]
    result = pd.DataFrame(
        stages,
        columns=["stage", "observed_count", "paper_count"],
    )
    result["difference"] = result.observed_count - result.paper_count
    result["matches_paper"] = result.difference == 0
    return result
