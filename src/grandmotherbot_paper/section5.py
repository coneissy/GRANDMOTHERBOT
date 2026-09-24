from __future__ import annotations

from decimal import Decimal

import pandas as pd

from .constants import KNOWN_PATTERN_BY_SEARCHER
from .liquidity import pair_class
from .markout import median_gr_curve
from .reproduction import valid_observations


def _observations_by_searcher(markouts: pd.DataFrame):
    valid = valid_observations(markouts)
    labels = markouts.groupby("tx_hash")["searcher_label"].first().to_dict()
    grouped = {}
    for tx_hash, observation in valid.items():
        label = labels.get(tx_hash)
        if label:
            grouped.setdefault(str(label), []).append(observation)
    return grouped


def searcher_trade_size_return(scored: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "searcher_label",
        "median_trade_volume_usd",
        "median_gross_return_bps",
        "estimated_revenue_usd",
        "pattern",
    ]
    if scored.empty:
        return pd.DataFrame(columns=columns)

    rows = []
    for label, group in scored.groupby("searcher_label"):
        profile = KNOWN_PATTERN_BY_SEARCHER.get(str(label))
        pattern = profile[1] if profile else None
        if pattern == 3:
            continue
        rows.append(
            {
                "searcher_label": str(label),
                "median_trade_volume_usd": group.dex_volume_usd.median(),
                "median_gross_return_bps": group.gross_return.median() * 10_000,
                "estimated_revenue_usd": group.ev_usd.sum(),
                "pattern": pattern,
            }
        )
    return pd.DataFrame(rows, columns=columns)


def gross_return_cdf(scored: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for pattern in (1, 2):
        values = []
        for _, row in scored.iterrows():
            profile = KNOWN_PATTERN_BY_SEARCHER.get(str(row.searcher_label))
            if profile and profile[1] == pattern:
                values.append(float(row.gross_return) * 10_000)
        values.sort()
        n = len(values)
        for rank, value in enumerate(values, start=1):
            rows.append(
                {
                    "pattern": pattern,
                    "gross_return_bps": value,
                    "cdf": rank / n,
                }
            )
    return pd.DataFrame(
        rows,
        columns=["pattern", "gross_return_bps", "cdf"],
    )


def hedge_decline_by_searcher(markouts: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for label, observations in _observations_by_searcher(markouts).items():
        profile = KNOWN_PATTERN_BY_SEARCHER.get(label)
        if not profile or profile[1] == 3:
            continue
        curve = median_gr_curve(observations)
        if not curve:
            continue

        peak_horizon = max(curve, key=curve.get)
        peak_value = curve[peak_horizon]
        target = peak_horizon + Decimal("3.0")
        later = [horizon for horizon in curve if horizon >= target]
        if not later or peak_value == 0:
            continue

        decline_horizon = min(later)
        decline = (peak_value - curve[decline_horizon]) / abs(peak_value)
        rows.append(
            {
                "searcher_label": label,
                "pattern": profile[1],
                "peak_horizon_s": float(peak_horizon),
                "decline_horizon_s": float(decline_horizon),
                "decline_3s": float(decline),
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "searcher_label",
            "pattern",
            "peak_horizon_s",
            "decline_horizon_s",
            "decline_3s",
        ],
    )


def liquidity_regime(token_pairs: pd.DataFrame) -> pd.DataFrame:
    required = {"tx_hash", "searcher_label", "token_a", "token_b", "volume_usd"}
    missing = required - set(token_pairs.columns)
    if missing:
        raise ValueError(
            "token_pairs missing required columns: " + ", ".join(sorted(missing))
        )

    work = token_pairs.copy()
    work["pair_class"] = [
        pair_class(a, b) for a, b in zip(work.token_a, work.token_b)
    ]

    rows = []
    for label, group in work.groupby("searcher_label"):
        total_count = len(group)
        total_volume = group.volume_usd.sum()
        for pair_type in ("Major-Major", "Major-ALT", "ALT-ALT"):
            subset = group[group.pair_class == pair_type]
            rows.append(
                {
                    "searcher_label": str(label),
                    "pair_class": pair_type,
                    "trade_count": len(subset),
                    "trade_count_share": len(subset) / total_count
                    if total_count
                    else 0,
                    "volume_usd": subset.volume_usd.sum(),
                    "volume_share": subset.volume_usd.sum() / total_volume
                    if total_volume
                    else 0,
                }
            )
    return pd.DataFrame(rows)


def hedge_liquidity_correlation(
    token_pairs: pd.DataFrame,
    markouts: pd.DataFrame,
) -> pd.DataFrame:
    mix = liquidity_regime(token_pairs)
    major = mix[mix.pair_class == "Major-Major"][
        ["searcher_label", "trade_count_share", "volume_share"]
    ]
    decline = hedge_decline_by_searcher(markouts)
    joined = major.merge(decline, on="searcher_label", how="inner")

    if joined.empty:
        return pd.DataFrame(
            columns=["measure", "spearman_rho", "n_searchers"]
        )

    from .correlation import spearman

    return pd.DataFrame(
        [
            {
                "measure": "trade_count",
                "spearman_rho": spearman(
                    joined.trade_count_share.tolist(),
                    joined.decline_3s.tolist(),
                ),
                "n_searchers": len(joined),
            },
            {
                "measure": "trade_volume",
                "spearman_rho": spearman(
                    joined.volume_share.tolist(),
                    joined.decline_3s.tolist(),
                ),
                "n_searchers": len(joined),
            },
        ]
    )
