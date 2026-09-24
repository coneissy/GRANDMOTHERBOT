from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

import pandas as pd

from .builder import builder_profit_usd, aggregated_profit, is_subsidized_block
from .constants import HORIZONS, PAPER_END_BLOCK, PAPER_START_BLOCK
from .identification import CandidateTransaction, passes_all_heuristics
from .liquidity import pair_class
from .markout import MarkoutPoint, TradeObservation, median_gr_curve, optimal_horizon
from .profitability import estimated_ev, estimated_pnl, profit_margin, inventory_adjustment_like
from .reconstruction import Swap, reconstruct_effective_trade
from .patterns import published_searcher_profile
from .constants import KNOWN_PATTERN_BY_SEARCHER

def _bool(v):
    return str(v).strip().lower() in {"1","true","t","yes","y"}

def identify(df: pd.DataFrame) -> pd.DataFrame:
    keep=[]
    for _,r in df.iterrows():
        tx=CandidateTransaction(
            _bool(r["observed_public_mempool"]),
            _bool(r["first_swap_in_pool_direction"]),
            _bool(r["atomic_mev"]),
            _bool(r["liquidation"]),
            _bool(r["ofa_backrun"]),
            _bool(r["known_router"]),
            _bool(r["labeled_trading_bot"]),
            _bool(r["ens_named_eoa_controller"]),
            _bool(r["erc721_transfer"]),
            _bool(r["final_pair_major_cex_listed"]),
            str(r["from_address"]),
        )
        if passes_all_heuristics(tx):
            keep.append(r)
    return pd.DataFrame(keep,columns=df.columns)

def reconstruct(swaps: pd.DataFrame):
    grouped=defaultdict(list)
    for _,r in swaps.iterrows():
        grouped[str(r.tx_hash)].append(
            Swap(str(r.token_in),str(r.token_out),Decimal(str(r.amount_in)),Decimal(str(r.amount_out)),int(r.log_index))
        )
    return {tx:reconstruct_effective_trade(tuple(rows)) for tx,rows in grouped.items()}

def build_observations(markouts: pd.DataFrame) -> dict[str, TradeObservation]:
    out={}
    for tx,g in markouts.groupby("tx_hash"):
        first=g.iloc[0]
        points=tuple(
            MarkoutPoint(Decimal(str(r.horizon_s)),Decimal(str(r.token_a_usdt_mid)),Decimal(str(r.token_b_usdt_mid)))
            for _,r in g.sort_values("horizon_s").iterrows()
        )
        out[str(tx)]=TradeObservation(
            Decimal(str(first.amount_a)),Decimal(str(first.amount_b)),
            Decimal(str(first.dex_volume_usd)),Decimal(str(first.cex_taker_fees_usd)),points
        )
    return out

def compute_searcher_tstars(markouts: pd.DataFrame) -> pd.DataFrame:
    obs_map=build_observations(markouts)
    searcher_by_tx=markouts.groupby("tx_hash")["searcher_label"].first().to_dict()
    by_searcher=defaultdict(list)
    for tx,obs in obs_map.items():
        label=searcher_by_tx.get(tx)
        if label:
            by_searcher[label].append(obs)
    rows=[]
    for label,obs in by_searcher.items():
        profile=published_searcher_profile(label) if label in KNOWN_PATTERN_BY_SEARCHER else None
        # The paper excludes Pattern 3 searchers from revenue/PnL estimation.
        if profile and profile["pattern"] == 3:
            t=None
        else:
            t=optimal_horizon(obs)
        rows.append({"searcher_label":label,"computed_t_star_s":t,"published_t_star_s":profile["optimal_execution_horizon_s"] if profile else None})
    return pd.DataFrame(rows)

def score(markouts: pd.DataFrame, tstars: dict[str,Decimal|float|None]) -> pd.DataFrame:
    rows=[]
    for tx,g in markouts.groupby("tx_hash"):
        r0=g.iloc[0]
        label=str(r0.searcher_label)
        t=tstars.get(label)
        if t is None:
            continue
        row=g[g.horizon_s.astype(float)==float(t)]
        if row.empty:
            continue
        r=row.iloc[0]
        mr=r.amount_a*r.token_a_usdt_mid-r.amount_b*r.token_b_usdt_mid-r.cex_taker_fees_usd
        ev=mr-r.base_fees_usd
        pnl=ev-r.builder_tips_usd
        rows.append({"tx_hash":tx,"searcher_label":label,"t_star_s":float(t),"mr_usd":mr,"ev_usd":ev,"builder_tips_usd":r.builder_tips_usd,"pnl_usd":pnl,"profit_margin":(pnl/ev if ev>0 else None)})
    return pd.DataFrame(rows)

def pair_mix_from_scored(scored: pd.DataFrame, token_pairs: pd.DataFrame) -> pd.DataFrame:
    m=token_pairs.copy()
    m["pair_class"]=[pair_class(a,b) for a,b in zip(m["token_a"],m["token_b"])]
    return m.groupby(["searcher_label","pair_class"]).agg(trades=("tx_hash","count"),volume_usd=("volume_usd","sum")).reset_index()

def builder_report(builder_blocks: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for _,r in builder_blocks.iterrows():
        from datetime import datetime
        dt=pd.to_datetime(r.slot_time,utc=True).to_pydatetime()
        bp=builder_profit_usd(
            Decimal(str(r.delta_coinbase_usd)),
            Decimal(str(r.bid_value_usd)),
            _bool(r.bid_adjusted),
            Decimal(str(r.bid_adjustment_delta_usd)),
            dt,
        )
        sp=Decimal(str(r.searcher_pnl_usd)) if "searcher_pnl_usd" in r and pd.notna(r.searcher_pnl_usd) else Decimal("0")
        agg=aggregated_profit(bp,sp)
        rows.append({"block_number":r.block_number,"builder":r.builder,"builder_profit_usd":bp,"searcher_pnl_usd":sp,"aggregated_profit_usd":agg,"subsidized":is_subsidized_block(bp,agg)})
    return pd.DataFrame(rows)

def validate_paper_block_range(df: pd.DataFrame) -> None:
    lo=int(df.block_number.min()); hi=int(df.block_number.max())
    if lo < PAPER_START_BLOCK or hi > PAPER_END_BLOCK:
        raise ValueError(f"block range {lo}-{hi} falls outside paper range {PAPER_START_BLOCK}-{PAPER_END_BLOCK}")
