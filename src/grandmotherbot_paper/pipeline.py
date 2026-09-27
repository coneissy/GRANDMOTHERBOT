from collections import defaultdict
from decimal import Decimal

import pandas as pd

from .builder import aggregated_profit, is_subsidized_block
from .identification import CandidateTransaction, passes_all_heuristics
from .markout import MarkoutPoint, TradeObservation, markout_revenue, optimal_horizon
from .profitability import estimated_ev, estimated_pnl, inventory_adjustment_like
from .reconstruction import Swap, reconstruct_effective_trade


def _bool(value) -> bool:
    if pd.isna(value):
        raise ValueError("boolean evidence field cannot be null")
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y"}


def identify_transactions(transactions, swaps_by_tx=None):
    """Apply H1-H6 plus manual exclusions to transaction evidence.

    Reconstruction is intentionally accepted as a separate upstream stage because
    H6 depends on the reconstructed final token pair in the paper methodology.
    """
    identified = []
    required = {
        "observed_public_mempool", "first_swap_in_pool_direction", "atomic_mev",
        "liquidation", "ofa_backrun", "known_router", "labeled_trading_bot",
        "ens_named_eoa_controller", "erc721_transfer", "final_pair_major_cex_listed",
        "from_address",
    }
    missing = required - set(transactions.columns)
    if missing:
        raise ValueError("transactions missing identification fields: " + ", ".join(sorted(missing)))
    for _, row in transactions.iterrows():
        tx = CandidateTransaction(
            observed_public_mempool=_bool(row["observed_public_mempool"]),
            first_swap_in_pool_direction=_bool(row["first_swap_in_pool_direction"]),
            atomic_mev=_bool(row["atomic_mev"]),
            liquidation=_bool(row["liquidation"]),
            ofa_backrun=_bool(row["ofa_backrun"]),
            known_router=_bool(row["known_router"]),
            labeled_trading_bot=_bool(row["labeled_trading_bot"]),
            ens_named_eoa_controller=_bool(row["ens_named_eoa_controller"]),
            erc721_transfer=_bool(row["erc721_transfer"]),
            final_pair_major_cex_listed=_bool(row["final_pair_major_cex_listed"]),
            from_address=str(row["from_address"]),
        )
        if passes_all_heuristics(tx):
            identified.append(row)
    return identified


def reconstruct_rows(swaps):
    grouped = defaultdict(list)
    for _, row in swaps.iterrows():
        grouped[str(row["tx_hash"])].append(
            Swap(
                str(row["token_in"]), str(row["token_out"]),
                Decimal(str(row["amount_in"])), Decimal(str(row["amount_out"])),
                int(row["log_index"]),
            )
        )
    return {
        tx_hash: reconstruct_effective_trade(tuple(rows))
        for tx_hash, rows in grouped.items()
    }


def searcher_horizon(observations_by_searcher):
    return {searcher: optimal_horizon(observations) for searcher, observations in observations_by_searcher.items()}


def build_markout_observation(rows):
    if rows.empty:
        raise ValueError("markout rows are required")
    first = rows.iloc[0]
    points = tuple(
        MarkoutPoint(
            Decimal(str(row.horizon_s)),
            Decimal(str(row.token_a_usdt_mid)),
            Decimal(str(row.token_b_usdt_mid)),
        )
        for _, row in rows.sort_values("horizon_s").iterrows()
    )
    return TradeObservation(
        amount_a=Decimal(str(first.amount_a)),
        amount_b=Decimal(str(first.amount_b)),
        dex_volume_usd=Decimal(str(first.dex_volume_usd)),
        cex_taker_fees_usd=Decimal(str(first.cex_taker_fees_usd)),
        markouts=points,
        base_fees_usd=Decimal(str(first.base_fees_usd)),
    )


def profitable_trade_statistics(
    observation: TradeObservation,
    t_star: Decimal,
    builder_tips_usd: Decimal,
):
    """Score a trade at the research-selected searcher execution horizon."""
    if t_star not in {point.horizon_s for point in observation.markouts}:
        raise ValueError("selected t* is missing from the trade markout window")
    revenues = [
        markout_revenue(
            observation.amount_a,
            observation.amount_b,
            point,
            observation.cex_taker_fees_usd,
        )
        for point in observation.markouts
    ]
    if inventory_adjustment_like(revenues, observation.base_fees_usd):
        return {"inventory_adjustment": True, "ev_usd": None, "pnl_usd": None, "profit_margin": None}
    selected = next(point for point in observation.markouts if point.horizon_s == t_star)
    mr = markout_revenue(
        observation.amount_a,
        observation.amount_b,
        selected,
        observation.cex_taker_fees_usd,
    )
    ev = estimated_ev(mr, observation.base_fees_usd)
    pnl = estimated_pnl(ev, builder_tips_usd)
    return {
        "inventory_adjustment": False,
        "ev_usd": ev,
        "pnl_usd": pnl,
        "profit_margin": pnl / ev if ev > 0 else None,
    }


def corrected_block_profit(builder_profit, searcher_pnl):
    return aggregated_profit(builder_profit, searcher_pnl)


def subsidy_flag(builder_profit, searcher_pnl):
    return is_subsidized_block(builder_profit, builder_profit + searcher_pnl)
