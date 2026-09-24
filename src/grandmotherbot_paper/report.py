from __future__ import annotations

from pathlib import Path
import json
import pandas as pd

from .constants import (
    HORIZONS,
    KNOWN_PATTERN_BY_SEARCHER,
    PAPER_END_BLOCK,
    PAPER_END_DATE,
    PAPER_START_BLOCK,
    PAPER_START_DATE,
)
from .concentration import hhi
from .identification import CandidateTransaction, passes_all_heuristics
from .liquidity import pair_class
from .searcher_analysis import summarize_searchers
from .reproduction import builder_report
from .patterns import published_searcher_profile, all_published_profiles
from .landscape import daily_counts_and_volume, weekly_searcher_volume, weekly_hhi

def as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1","true","t","yes","y"}

def identify_transactions(transactions: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for _, r in transactions.iterrows():
        tx=CandidateTransaction(
            as_bool(r["observed_public_mempool"]),
            as_bool(r["first_swap_in_pool_direction"]),
            as_bool(r["atomic_mev"]),
            as_bool(r["liquidation"]),
            as_bool(r["ofa_backrun"]),
            as_bool(r["known_router"]),
            as_bool(r["labeled_trading_bot"]),
            as_bool(r["ens_named_eoa_controller"]),
            as_bool(r["erc721_transfer"]),
            as_bool(r["final_pair_major_cex_listed"]),
            str(r.get("from_address","")),
        )
        if passes_all_heuristics(tx):
            rows.append(r)
    return pd.DataFrame(rows, columns=transactions.columns)

def compute_t_star(markouts: pd.DataFrame) -> pd.DataFrame:
    required={"searcher_label","tx_hash","horizon_s","amount_a","amount_b","dex_volume_usd","token_a_usdt_mid","token_b_usdt_mid","cex_taker_fees_usd"}
    missing=required-markouts.columns
    if missing:
        raise ValueError("markouts missing: "+", ".join(sorted(missing)))
    m=markouts.copy()
    m["mr_usd"]=m["amount_a"]*m["token_a_usdt_mid"]-m["amount_b"]*m["token_b_usdt_mid"]-m["cex_taker_fees_usd"]
    m["gr"]=m["mr_usd"]/m["dex_volume_usd"]
    complete=m.groupby("tx_hash")["horizon_s"].nunique().eq(len(HORIZONS))
    complete_txs=set(complete[complete].index)
    m=m[m.tx_hash.isin(complete_txs)]
    med=m.groupby(["searcher_label","horizon_s"],as_index=False)["gr"].median()
    out=[]
    for searcher,g in med.groupby("searcher_label"):
        profile=published_searcher_profile(searcher) if searcher in KNOWN_PATTERN_BY_SEARCHER else None
        if profile and profile["pattern"]==3:
            continue
        best=g["gr"].max()
        chosen=g[g["gr"]==best]["horizon_s"].max()
        out.append({"searcher_label":searcher,"computed_t_star_s":chosen,"median_gr_at_t_star":best})
    return pd.DataFrame(out)

def evaluate_trades(markouts: pd.DataFrame, tstar: dict) -> pd.DataFrame:
    required={"searcher_label","tx_hash","horizon_s","amount_a","amount_b","dex_volume_usd","token_a_usdt_mid","token_b_usdt_mid","cex_taker_fees_usd","base_fees_usd","builder_tips_usd"}
    missing=required-markouts.columns
    if missing:
        raise ValueError("markouts missing: "+", ".join(sorted(missing)))
    rows=[]
    for tx_hash,g in markouts.groupby("tx_hash"):
        label=str(g.iloc[0]["searcher_label"])
        horizon=tstar.get(label)
        if pd.isna(horizon) if horizon is not None else True:
            continue
        point=g[g["horizon_s"].astype(float)==float(horizon)]
        if point.empty:
            continue
        r=point.iloc[0]
        mr=r["amount_a"]*r["token_a_usdt_mid"]-r["amount_b"]*r["token_b_usdt_mid"]-r["cex_taker_fees_usd"]
        ev=mr-r["base_fees_usd"]
        pnl=ev-r["builder_tips_usd"]
        rows.append({
            "tx_hash":tx_hash,
            "searcher_label":label,
            "t_star_s":horizon,
            "mr_usd":mr,
            "ev_usd":ev,
            "builder_tips_usd":r["builder_tips_usd"],
            "pnl_usd":pnl,
            "profit_margin":(pnl/ev if ev>0 else None),
        })
    return pd.DataFrame(rows)

def weekly_share_and_hhi(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    work=df.copy()
    work["week"]=pd.to_datetime(work["slot_time"],utc=True).dt.to_period("W").astype(str)
    rows=[]
    for week,g in work.groupby("week"):
        by=g.groupby("searcher_label")[value_col].sum()
        total=by.sum()
        for s,v in by.items():
            rows.append({"week":week,"searcher_label":s,"value":v,"share":(v/total if total else 0),"hhi":hhi(by.tolist())})
    return pd.DataFrame(rows)

def pair_mix(df: pd.DataFrame) -> pd.DataFrame:
    work=df.copy()
    work["pair_class"]=[pair_class(a,b) for a,b in zip(work["token_a"],work["token_b"])]
    return work.groupby(["searcher_label","pair_class"]).agg(trades=("tx_hash","count"),volume_usd=("volume_usd","sum")).reset_index()

def build_report(input_dir: str, output_dir: str) -> dict:
    root=Path(input_dir); out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    transactions=pd.read_csv(root/"transactions.csv")
    markouts=pd.read_csv(root/"markouts.csv")
    identified=identify_transactions(transactions)
    identified.to_csv(out/"identified_cex_dex.csv",index=False)
    tstar_df=compute_t_star(markouts)
    tstar_df.to_csv(out/"computed_t_star.csv",index=False)
    tstar=dict(zip(tstar_df.searcher_label,tstar_df.computed_t_star_s))
    trades=evaluate_trades(markouts,tstar)
    if not trades.empty:
        trades.to_csv(out/"trade_profitability.csv",index=False)
        summarize_searchers(trades, markouts).to_csv(out/"searcher_profitability.csv",index=False)
    if {"slot_time","tx_hash","volume_usd","searcher_label"}.issubset(identified.columns):
        daily_counts_and_volume(identified).to_csv(out/"daily_landscape.csv",index=False)
        weekly_searcher_volume(identified).to_csv(out/"weekly_searcher_volume.csv",index=False)
        weekly_hhi(identified, "volume_usd").to_csv(out/"weekly_volume_hhi.csv",index=False)
    if (root/"builder_blocks.csv").exists():
        blocks=pd.read_csv(root/"builder_blocks.csv")
        builder_report(blocks).to_csv(out/"builder_profitability.csv",index=False)
    summary={
        "paper_period":{"start_block":PAPER_START_BLOCK,"end_block":PAPER_END_BLOCK,"start_date":PAPER_START_DATE,"end_date":PAPER_END_DATE},
        "horizons":list(map(str,HORIZONS)),
        "input_transactions":len(transactions),
        "identified_transactions":len(identified),
        "computed_searchers":len(tstar_df),
        "profiles_in_paper":len(KNOWN_PATTERN_BY_SEARCHER),
    }
    if not trades.empty:
        summary.update({
            "trade_rows_scored":len(trades),
            "estimated_ev_usd":float(trades.ev_usd.sum()),
            "estimated_pnl_usd":float(trades.pnl_usd.sum()),
            "profitable_trades":int((trades.pnl_usd>=0).sum()),
            "unprofitable_trades":int((trades.pnl_usd<0).sum()),
        })
    (out/"run_summary.json").write_text(json.dumps(summary,indent=2,default=str),encoding="utf-8")
    return summary
