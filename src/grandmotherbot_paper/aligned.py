from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import pandas as pd

from .constants import HORIZONS, KNOWN_PATTERN_BY_SEARCHER
from .dynamic_pipeline import DynamicPipelineConfig
from .profitability import estimated_ev, estimated_pnl, profit_margin
from .reproduction import build_observations, build_paper_markouts, compute_searcher_tstars


@dataclass(frozen=True)
class ResearchStageCounts:
    input_candidates: int
    h1_h6_candidates: int
    reconstructed: int
    contract_mapped: int
    complete_tardis: int
    inventory_adjustments: int
    final_arbitrages: int
    profitability_searchers: int


def _require(df: pd.DataFrame, columns: set[str], name: str) -> None:
    missing = sorted(columns - set(df.columns))
    if missing:
        raise ValueError(f"{name} missing required columns: {', '.join(missing)}")


def _decimal(v: object) -> Decimal:
    return Decimal(str(v))


def attach_economics(markouts: pd.DataFrame, economics: pd.DataFrame) -> pd.DataFrame:
    """Attach normalized on-chain economics without changing the markout sample."""
    _require(economics, {"tx_hash", "base_fees_usd", "builder_tips_usd"}, "economics")
    out = markouts.copy()
    econ = economics.drop_duplicates("tx_hash").copy()
    out["tx_hash"] = out["tx_hash"].astype(str)
    econ["tx_hash"] = econ["tx_hash"].astype(str)
    overlap = set(out.columns) & (set(econ.columns) - {"tx_hash"})
    if overlap:
        out = out.drop(columns=sorted(overlap))
    return out.merge(econ, on="tx_hash", how="inner", validate="many_to_one")


def compute_aligned_tstars(markouts: pd.DataFrame) -> pd.DataFrame:
    """Compute t* from cross-trade median GR, never from published values."""
    _require(markouts, {"tx_hash", "searcher_label", "horizon_s"}, "markouts")
    result = compute_searcher_tstars(markouts)
    if result.empty:
        return result
    result["published_pattern"] = result["searcher_label"].map(
        lambda s: KNOWN_PATTERN_BY_SEARCHER.get(str(s), (None, None))[1]
    )
    return result


def score_aligned(markouts: pd.DataFrame, tstars: pd.DataFrame) -> pd.DataFrame:
    """Apply Eq. (2): EV = MR(t*) - base fees; PnL = EV - builder tips.

    EV <= 0 trades remain in PnL output and receive a null profit margin.
    """
    _require(markouts, {
        "tx_hash", "searcher_label", "horizon_s", "amount_a", "amount_b",
        "token_a_usdt_mid", "token_b_usdt_mid", "cex_taker_fees_usd",
        "dex_volume_usd", "base_fees_usd", "builder_tips_usd",
    }, "markouts")
    valid_tstars = {
        str(r.searcher_label): _decimal(r.computed_t_star_s)
        for r in tstars.itertuples(index=False)
        if pd.notna(r.computed_t_star_s)
    }
    rows = []
    for tx_hash, group in markouts.groupby(markouts.tx_hash.astype(str), sort=False):
        label = str(group.iloc[0].searcher_label)
        t_star = valid_tstars.get(label)
        if t_star is None:
            continue
        selected = group[group.horizon_s.map(_decimal) == t_star]
        if selected.empty:
            raise ValueError(f"{tx_hash}: missing computed t* horizon {t_star}")
        row = selected.iloc[0]
        mr = (
            _decimal(row.amount_a) * _decimal(row.token_a_usdt_mid)
            - _decimal(row.amount_b) * _decimal(row.token_b_usdt_mid)
            - _decimal(row.cex_taker_fees_usd)
        )
        ev = estimated_ev(mr, _decimal(row.base_fees_usd))
        pnl = estimated_pnl(ev, _decimal(row.builder_tips_usd))
        margin = profit_margin(ev, pnl)
        rows.append({
            "tx_hash": tx_hash,
            "searcher_label": label,
            "t_star_s": t_star,
            "mr_usd": mr,
            "ev_usd": ev,
            "base_fees_usd": _decimal(row.base_fees_usd),
            "builder_tips_usd": _decimal(row.builder_tips_usd),
            "pnl_usd": pnl,
            "profit_margin": margin,
            "dex_volume_usd": _decimal(row.dex_volume_usd),
        })
    return pd.DataFrame(rows)


def run_aligned_economics(
    transactions: pd.DataFrame,
    swaps: pd.DataFrame,
    binance_tokens,
    economics: pd.DataFrame,
    config: DynamicPipelineConfig,
    *,
    apply_h1_h6: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run the paper-aligned markout and economic estimator."""
    markouts = build_paper_markouts(
        transactions, swaps, binance_tokens, config, apply_h1_h6=apply_h1_h6
    )
    if markouts.empty:
        return pd.DataFrame(), pd.DataFrame()

    enriched = attach_economics(markouts, economics)

    expected = {str(h) for h in HORIZONS}
    complete_tx = [
        str(tx_hash) for tx_hash, group in enriched.groupby(enriched.tx_hash.astype(str))
        if set(group.horizon_s.astype(str)) == expected
    ]
    enriched = enriched[enriched.tx_hash.astype(str).isin(complete_tx)].copy()

    observations = build_observations(enriched)
    inventory_tx = {
        tx_hash for tx_hash, obs in observations.items()
        if all(
            obs.amount_a * p.token_a_usdt_mid
            - obs.amount_b * p.token_b_usdt_mid
            - obs.cex_taker_fees_usd < obs.base_fees_usd
            for p in obs.markouts
        )
    }
    if inventory_tx:
        enriched = enriched[~enriched.tx_hash.astype(str).isin(inventory_tx)].copy()

    tstars = compute_aligned_tstars(enriched)
    return score_aligned(enriched, tstars), tstars
