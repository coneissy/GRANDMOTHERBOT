from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

import pandas as pd

from .builder import (
    aggregated_profit,
    aggregated_profit_margin,
    builder_profit_from_eth_usd,
    builder_profit_usd,
    is_subsidized_block,
)
from .constants import HORIZONS, PAPER_END_BLOCK, PAPER_START_BLOCK
from .identification import CandidateTransaction, passes_all_heuristics
from .liquidity import pair_class
from .markout import (
    MarkoutPoint,
    TradeObservation,
    complete_markout_window,
    inventory_adjustment_like_observation,
    optimal_horizon,
)
from .profitability import estimated_ev, estimated_pnl, profit_margin
from .reconstruction import Swap, reconstruct_effective_trade
from .patterns import published_searcher_profile
from .constants import KNOWN_PATTERN_BY_SEARCHER


def _bool(v):
    return str(v).strip().lower() in {"1", "true", "t", "yes", "y"}


def identify(df: pd.DataFrame) -> pd.DataFrame:
    keep = []
    for _, row in df.iterrows():
        tx = CandidateTransaction(
            _bool(row["observed_public_mempool"]),
            _bool(row["first_swap_in_pool_direction"]),
            _bool(row["atomic_mev"]),
            _bool(row["liquidation"]),
            _bool(row["ofa_backrun"]),
            _bool(row["known_router"]),
            _bool(row["labeled_trading_bot"]),
            _bool(row["ens_named_eoa_controller"]),
            _bool(row["erc721_transfer"]),
            _bool(row["final_pair_major_cex_listed"]),
            str(row["from_address"]),
        )
        if passes_all_heuristics(tx):
            keep.append(row)
    return pd.DataFrame(keep, columns=df.columns)


def reconstruct(swaps: pd.DataFrame):
    grouped = defaultdict(list)
    for _, row in swaps.iterrows():
        grouped[str(row.tx_hash)].append(
            Swap(
                str(row.token_in),
                str(row.token_out),
                Decimal(str(row.amount_in)),
                Decimal(str(row.amount_out)),
                int(row.log_index),
            )
        )
    return {
        tx_hash: reconstruct_effective_trade(tuple(rows))
        for tx_hash, rows in grouped.items()
    }


def build_observations(markouts: pd.DataFrame) -> dict[str, TradeObservation]:
    out = {}
    for tx_hash, group in markouts.groupby("tx_hash"):
        ordered = group.sort_values("horizon_s")
        first = ordered.iloc[0]
        points = tuple(
            MarkoutPoint(
                Decimal(str(row.horizon_s)),
                Decimal(str(row.token_a_usdt_mid)),
                Decimal(str(row.token_b_usdt_mid)),
            )
            for _, row in ordered.iterrows()
        )
        out[str(tx_hash)] = TradeObservation(
            amount_a=Decimal(str(first.amount_a)),
            amount_b=Decimal(str(first.amount_b)),
            dex_volume_usd=Decimal(str(first.dex_volume_usd)),
            cex_taker_fees_usd=Decimal(str(first.cex_taker_fees_usd)),
            markouts=points,
            base_fees_usd=(
                Decimal(str(first.base_fees_usd))
                if "base_fees_usd" in ordered.columns
                else Decimal("0")
            ),
        )
    return out


def valid_observations(markouts: pd.DataFrame) -> dict[str, TradeObservation]:
    observations = build_observations(markouts)
    return {
        tx_hash: observation
        for tx_hash, observation in observations.items()
        if complete_markout_window(observation)
        and not inventory_adjustment_like_observation(observation)
    }


def compute_searcher_tstars(markouts: pd.DataFrame) -> pd.DataFrame:
    observations = valid_observations(markouts)
    searcher_by_tx = (
        markouts.groupby("tx_hash")["searcher_label"].first().to_dict()
    )

    grouped = defaultdict(list)
    for tx_hash, observation in observations.items():
        searcher = searcher_by_tx.get(tx_hash)
        if searcher:
            grouped[str(searcher)].append(observation)

    rows = []
    for searcher, searcher_observations in grouped.items():
        profile = (
            published_searcher_profile(searcher)
            if searcher in KNOWN_PATTERN_BY_SEARCHER
            else None
        )
        pattern = profile["pattern"] if profile else None
        t_star = None if pattern == 3 else optimal_horizon(searcher_observations)
        rows.append(
            {
                "searcher_label": searcher,
                "computed_t_star_s": t_star,
                "published_t_star_s": (
                    profile["optimal_execution_horizon_s"]
                    if profile
                    else None
                ),
                "pattern": pattern,
                "valid_trade_count": len(searcher_observations),
            }
        )
    return pd.DataFrame(rows)


def score(
    markouts: pd.DataFrame,
    tstars: dict[str, Decimal | float | None],
) -> pd.DataFrame:
    observations = valid_observations(markouts)
    rows = []

    for tx_hash, observation in observations.items():
        group = markouts[markouts.tx_hash.astype(str) == str(tx_hash)]
        if group.empty:
            continue
        label = str(group.iloc[0].searcher_label)
        t_star = tstars.get(label)
        if t_star is None:
            continue

        selected = group[group.horizon_s.astype(float) == float(t_star)]
        if selected.empty:
            continue
        row = selected.iloc[0]

        mr = (
            Decimal(str(row.amount_a)) * Decimal(str(row.token_a_usdt_mid))
            - Decimal(str(row.amount_b)) * Decimal(str(row.token_b_usdt_mid))
            - Decimal(str(row.cex_taker_fees_usd))
        )
        ev = estimated_ev(mr, Decimal(str(row.base_fees_usd)))
        pnl = estimated_pnl(ev, Decimal(str(row.builder_tips_usd)))
        margin = profit_margin(ev, pnl)

        rows.append(
            {
                "tx_hash": tx_hash,
                "searcher_label": label,
                "t_star_s": float(t_star),
                "mr_usd": float(mr),
                "ev_usd": float(ev),
                "builder_tips_usd": float(row.builder_tips_usd),
                "pnl_usd": float(pnl),
                "profit_margin": float(margin) if margin is not None else None,
                "gross_return": float(mr / Decimal(str(row.dex_volume_usd))),
                "dex_volume_usd": float(row.dex_volume_usd),
            }
        )
    return pd.DataFrame(rows)


def build_effective_token_pairs(
    transactions: pd.DataFrame,
    swaps: pd.DataFrame,
) -> pd.DataFrame:
    """Reconstruct the final bought/sold pair from sequential DEX swaps."""
    required_tx = {"tx_hash", "searcher_label", "volume_usd"}
    missing_tx = required_tx - set(transactions.columns)
    if missing_tx:
        raise ValueError(
            "transactions missing token-pair fields: " + ", ".join(sorted(missing_tx))
        )

    required_swaps = {
        "tx_hash", "log_index", "token_in", "token_out", "amount_in", "amount_out"
    }
    missing_swaps = required_swaps - set(swaps.columns)
    if missing_swaps:
        raise ValueError(
            "swaps missing reconstruction fields: " + ", ".join(sorted(missing_swaps))
        )

    reconstructed = reconstruct(swaps)
    tx = transactions.copy()
    tx["tx_hash"] = tx.tx_hash.astype(str)
    tx = tx.drop_duplicates("tx_hash").set_index("tx_hash")

    rows = []
    for tx_hash, effective in reconstructed.items():
        if tx_hash not in tx.index:
            continue
        source = tx.loc[tx_hash]
        if pd.isna(source.searcher_label) or pd.isna(source.volume_usd):
            continue
        rows.append(
            {
                "tx_hash": tx_hash,
                "searcher_label": str(source.searcher_label),
                "token_a": effective.token_bought,
                "token_b": effective.token_sold,
                "volume_usd": float(source.volume_usd),
            }
        )

    return pd.DataFrame(
        rows,
        columns=["tx_hash", "searcher_label", "token_a", "token_b", "volume_usd"],
    )


def pair_mix_from_scored(
    scored: pd.DataFrame,
    token_pairs: pd.DataFrame,
) -> pd.DataFrame:
    m = token_pairs.copy()
    m["pair_class"] = [
        pair_class(a, b)
        for a, b in zip(m["token_a"], m["token_b"])
    ]
    return (
        m.groupby(["searcher_label", "pair_class"])
        .agg(
            trades=("tx_hash", "count"),
            volume_usd=("volume_usd", "sum"),
        )
        .reset_index()
    )


def builder_report(builder_blocks: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in builder_blocks.iterrows():
        from datetime import datetime

        slot_time = pd.to_datetime(row.slot_time, utc=True).to_pydatetime()
        if {
            "delta_coinbase_eth",
            "bid_value_eth",
            "bid_adjustment_delta_eth",
            "eth_usdt_mid",
        }.issubset(builder_blocks.columns):
            builder_profit = builder_profit_from_eth_usd(
                Decimal(str(row.delta_coinbase_eth)),
                Decimal(str(row.bid_value_eth)),
                _bool(row.bid_adjusted),
                Decimal(str(row.bid_adjustment_delta_eth)),
                Decimal(str(row.eth_usdt_mid)),
                slot_time,
            )
            bid_value_usd = Decimal(str(row.bid_value_eth)) * Decimal(str(row.eth_usdt_mid))
            adjustment_usd = Decimal(str(row.bid_adjustment_delta_eth)) * Decimal(str(row.eth_usdt_mid))
        else:
            builder_profit = builder_profit_usd(
                Decimal(str(row.delta_coinbase_usd)),
                Decimal(str(row.bid_value_usd)),
                _bool(row.bid_adjusted),
                Decimal(str(row.bid_adjustment_delta_usd)),
                slot_time,
            )
            bid_value_usd = Decimal(str(row.bid_value_usd))
            adjustment_usd = Decimal(str(row.bid_adjustment_delta_usd))
        searcher_pnl = (
            Decimal(str(row.searcher_pnl_usd))
            if "searcher_pnl_usd" in row and pd.notna(row.searcher_pnl_usd)
            else Decimal("0")
        )
        aggregate = aggregated_profit(builder_profit, searcher_pnl)
        rows.append(
            {
                "block_number": row.block_number,
                "builder": row.builder,
                "builder_profit_usd": builder_profit,
                "searcher_pnl_usd": searcher_pnl,
                "aggregated_profit_usd": aggregate,
                "aggregated_profit_margin": aggregated_profit_margin(
                    aggregate,
                    bid_value_usd,
                    adjustment_usd,
                    slot_time,
                    _bool(row.bid_adjusted),
                ),
                "subsidized": is_subsidized_block(builder_profit, aggregate),
            }
        )
    return pd.DataFrame(rows)


def validate_paper_block_range(df: pd.DataFrame) -> None:
    lo = int(df.block_number.min())
    hi = int(df.block_number.max())
    if lo < PAPER_START_BLOCK or hi > PAPER_END_BLOCK:
        raise ValueError(
            f"block range {lo}-{hi} falls outside paper range "
            f"{PAPER_START_BLOCK}-{PAPER_END_BLOCK}"
        )
