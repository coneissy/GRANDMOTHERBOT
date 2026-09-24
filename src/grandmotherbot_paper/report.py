from __future__ import annotations

from pathlib import Path
import json

import pandas as pd

from .appendix_h import reconcile_appendix_h
from .concentration import hhi
from .constants import (
    HORIZONS,
    KNOWN_PATTERN_BY_SEARCHER,
    PAPER_END_BLOCK,
    PAPER_END_DATE,
    PAPER_START_BLOCK,
    PAPER_START_DATE,
)
from .identification import CandidateTransaction, passes_all_heuristics
from .liquidity import pair_class
from .reproduction import (
    build_effective_token_pairs,
    builder_report,
    score,
    compute_searcher_tstars,
)
from .searcher_analysis import summarize_searchers
from .section5 import (
    gross_return_cdf,
    hedge_decline_by_searcher,
    hedge_liquidity_correlation,
    liquidity_regime,
    searcher_trade_size_return,
)
from .landscape import daily_counts_and_volume, weekly_searcher_volume, weekly_hhi


def as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y"}


def identify_transactions(transactions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in transactions.iterrows():
        tx = CandidateTransaction(
            as_bool(row["observed_public_mempool"]),
            as_bool(row["first_swap_in_pool_direction"]),
            as_bool(row["atomic_mev"]),
            as_bool(row["liquidation"]),
            as_bool(row["ofa_backrun"]),
            as_bool(row["known_router"]),
            as_bool(row["labeled_trading_bot"]),
            as_bool(row["ens_named_eoa_controller"]),
            as_bool(row["erc721_transfer"]),
            as_bool(row["final_pair_major_cex_listed"]),
            str(row.get("from_address", "")),
        )
        if passes_all_heuristics(tx):
            rows.append(row)
    return pd.DataFrame(rows, columns=transactions.columns)


def weekly_share_and_hhi(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    work = df.copy()
    work["week"] = pd.to_datetime(work["slot_time"], utc=True).dt.to_period("W").astype(str)
    rows = []
    for week, group in work.groupby("week"):
        by_searcher = group.groupby("searcher_label")[value_col].sum()
        total = by_searcher.sum()
        for searcher, value in by_searcher.items():
            rows.append(
                {
                    "week": week,
                    "searcher_label": searcher,
                    "value": value,
                    "share": value / total if total else 0,
                    "hhi": hhi(by_searcher.tolist()),
                }
            )
    return pd.DataFrame(rows)


def pair_mix(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["pair_class"] = [
        pair_class(a, b) for a, b in zip(work["token_a"], work["token_b"])
    ]
    return (
        work.groupby(["searcher_label", "pair_class"])
        .agg(trades=("tx_hash", "count"), volume_usd=("volume_usd", "sum"))
        .reset_index()
    )


def build_report(input_dir: str, output_dir: str) -> dict:
    root = Path(input_dir)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    transactions = pd.read_csv(root / "transactions.csv")
    markouts = pd.read_csv(root / "markouts.csv")
    identified = identify_transactions(transactions)
    identified.to_csv(out / "identified_cex_dex.csv", index=False)

    tstar_df = compute_searcher_tstars(markouts)
    tstar_df.to_csv(out / "computed_t_star.csv", index=False)
    tstars = dict(zip(tstar_df.searcher_label, tstar_df.computed_t_star_s))

    trades = score(markouts, tstars)
    if not trades.empty:
        trades.to_csv(out / "trade_profitability.csv", index=False)
        summarize_searchers(trades, markouts).to_csv(
            out / "searcher_profitability.csv", index=False
        )

        searcher_trade_size_return(trades).to_csv(
            out / "section5_trade_size_return.csv", index=False
        )
        gross_return_cdf(trades).to_csv(
            out / "section5_gross_return_cdf.csv", index=False
        )

    if {"slot_time", "tx_hash", "volume_usd", "searcher_label"}.issubset(
        identified.columns
    ):
        daily_counts_and_volume(identified).to_csv(
            out / "daily_landscape.csv", index=False
        )
        weekly_searcher_volume(identified).to_csv(
            out / "weekly_searcher_volume.csv", index=False
        )
        weekly_hhi(identified, "volume_usd").to_csv(
            out / "weekly_volume_hhi.csv", index=False
        )

    token_pairs_path = root / "token_pairs.csv"
    if token_pairs_path.exists():
        token_pairs = pd.read_csv(token_pairs_path)
    elif (root / "swaps.csv").exists():
        token_pairs = build_effective_token_pairs(identified, pd.read_csv(root / "swaps.csv"))
        token_pairs.to_csv(out / "reconstructed_token_pairs.csv", index=False)
    else:
        token_pairs = None

    if token_pairs is not None:
        labeled = token_pairs[token_pairs.searcher_label.astype(str).isin(KNOWN_PATTERN_BY_SEARCHER)]
        liquidity_regime(labeled).to_csv(
            out / "section5_liquidity_regime.csv", index=False
        )
        hedge_liquidity_correlation(labeled, markouts).to_csv(
            out / "section5_hedge_liquidity_correlation.csv", index=False
        )

    hedge_decline_by_searcher(markouts).to_csv(
        out / "section5_hedge_decline.csv", index=False
    )

    appendix_h = reconcile_appendix_h(identified, markouts)
    appendix_h.to_csv(out / "appendix_h_reconciliation.csv", index=False)

    if (root / "builder_blocks.csv").exists():
        blocks = pd.read_csv(root / "builder_blocks.csv")
        builder_report(blocks).to_csv(out / "builder_profitability.csv", index=False)

    summary = {
        "paper_period": {
            "start_block": PAPER_START_BLOCK,
            "end_block": PAPER_END_BLOCK,
            "start_date": PAPER_START_DATE,
            "end_date": PAPER_END_DATE,
        },
        "horizons": list(map(str, HORIZONS)),
        "input_transactions": len(transactions),
        "identified_transactions": len(identified),
        "computed_searchers": len(tstar_df),
        "profiles_in_paper": len(KNOWN_PATTERN_BY_SEARCHER),
        "appendix_h_final_matches_paper": bool(
            appendix_h.loc[
                appendix_h.stage == "remaining_arbitrages", "matches_paper"
            ].iloc[0]
        ),
    }
    if not trades.empty:
        summary.update(
            {
                "trade_rows_scored": len(trades),
                "estimated_ev_usd": float(trades.ev_usd.sum()),
                "estimated_pnl_usd": float(trades.pnl_usd.sum()),
                "profitable_trades": int((trades.pnl_usd >= 0).sum()),
                "unprofitable_trades": int((trades.pnl_usd < 0).sum()),
            }
        )
    (out / "run_summary.json").write_text(
        json.dumps(summary, indent=2, default=str),
        encoding="utf-8",
    )
    return summary
