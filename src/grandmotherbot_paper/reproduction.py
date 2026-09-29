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


def validate_markout_data_contract(markouts: pd.DataFrame) -> None:
    """Fail closed before paper markout observations are constructed.

    This protects the locked 23-point paper window from duplicate, malformed,
    cross-pipeline, or explicitly mis-provenanced CEX observations. Provenance
    is enforced when its metadata is supplied; an absent provenance column is
    reported as an upstream data-readiness gap rather than silently inferred.
    """
    required = {
        "tx_hash",
        "horizon_s",
        "amount_a",
        "amount_b",
        "dex_volume_usd",
        "cex_taker_fees_usd",
        "token_a_usdt_mid",
        "token_b_usdt_mid",
    }
    missing = required - set(markouts.columns)
    if missing:
        raise ValueError(
            "markout data missing required columns: "
            + ", ".join(sorted(missing))
        )

    if markouts.empty:
        raise ValueError("markout data must not be empty")

    horizons = {
        Decimal(str(value))
        for value in markouts["horizon_s"].dropna().tolist()
    }
    invalid_horizons = horizons - set(HORIZONS)
    if invalid_horizons:
        raise ValueError(
            "markout data contains horizons outside the locked grid: "
            + ", ".join(sorted(map(str, invalid_horizons)))
        )

    duplicate_mask = markouts.duplicated(
        subset=["tx_hash", "horizon_s"],
        keep=False,
    )
    if duplicate_mask.any():
        duplicates = (
            markouts.loc[duplicate_mask, ["tx_hash", "horizon_s"]]
            .drop_duplicates()
            .to_dict("records")
        )
        raise ValueError(
            "duplicate (tx_hash, horizon_s) observations are not allowed: "
            + str(duplicates[:5])
        )

    for tx_hash, group in markouts.groupby("tx_hash"):
        tx_horizons = {Decimal(str(v)) for v in group["horizon_s"].tolist()}
        if len(tx_horizons) != len(HORIZONS) or tx_horizons != set(HORIZONS):
            missing_horizons = sorted(set(HORIZONS) - tx_horizons)
            raise ValueError(
                f"tx_hash={tx_hash} does not contain exactly the locked "
                f"23-horizon grid; missing={missing_horizons}"
            )

    numeric_columns = [
        "amount_a",
        "amount_b",
        "dex_volume_usd",
        "cex_taker_fees_usd",
        "token_a_usdt_mid",
        "token_b_usdt_mid",
    ]
    for column in numeric_columns:
        values = pd.to_numeric(markouts[column], errors="coerce")
        if values.isna().any():
            raise ValueError(f"markout column {column} contains non-numeric values")

    for column in ("token_a_usdt_mid", "token_b_usdt_mid", "dex_volume_usd"):
        values = pd.to_numeric(markouts[column], errors="coerce")
        if (values <= 0).any():
            raise ValueError(f"markout column {column} must contain only positive values")

    for column in ("amount_a", "amount_b", "cex_taker_fees_usd"):
        values = pd.to_numeric(markouts[column], errors="coerce")
        if (values < 0).any():
            raise ValueError(f"markout column {column} must contain only non-negative values")

    if "dataset_type" in markouts.columns:
        dataset_types = set(markouts["dataset_type"].dropna().astype(str))
        if dataset_types - {"paper_replication"}:
            raise ValueError(
                "paper markout pipeline received non-paper dataset_type values: "
                + ", ".join(sorted(dataset_types - {"paper_replication"}))
            )

    if "pipeline" in markouts.columns:
        pipelines = set(markouts["pipeline"].dropna().astype(str))
        if pipelines - {"paper_replication"}:
            raise ValueError(
                "paper markout pipeline received non-paper pipeline values: "
                + ", ".join(sorted(pipelines - {"paper_replication"}))
            )

    if "source" in markouts.columns:
        sources = set(markouts["source"].dropna().astype(str).str.lower())
        if sources - {"tardis"}:
            raise ValueError(
                "paper_replication markouts cannot use non-Tardis quote sources: "
                + ", ".join(sorted(sources - {"tardis"}))
            )

    if "quote_source" in markouts.columns:
        sources = set(markouts["quote_source"].dropna().astype(str).str.lower())
        if sources - {"tardis"}:
            raise ValueError(
                "paper_replication markouts cannot use non-Tardis quote sources: "
                + ", ".join(sorted(sources - {"tardis"}))
            )

    if "exchange" in markouts.columns:
        exchanges = set(markouts["exchange"].dropna().astype(str).str.lower())
        if exchanges - {"binance"}:
            raise ValueError(
                "paper_replication markouts cannot use non-Binance exchanges: "
                + ", ".join(sorted(exchanges - {"binance"}))
            )


def build_observations(markouts: pd.DataFrame) -> dict[str, TradeObservation]:
    validate_markout_data_contract(markouts)

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
