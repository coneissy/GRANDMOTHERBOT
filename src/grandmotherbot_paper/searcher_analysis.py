from __future__ import annotations
import pandas as pd

def summarize_searchers(scored: pd.DataFrame, source_markouts: pd.DataFrame) -> pd.DataFrame:
    if scored.empty:
        return scored
    base=source_markouts[["tx_hash","dex_volume_usd"]].drop_duplicates("tx_hash")
    w=scored.merge(base,on="tx_hash",how="left")
    rows=[]
    for label,g in w.groupby("searcher_label"):
        margins=g.loc[g.ev_usd>0,"profit_margin"].dropna()
        rows.append({
            "searcher_label":label,
            "total_volume_usd":g.dex_volume_usd.sum(),
            "estimated_revenue_usd":g.ev_usd.sum(),
            "builder_tips_usd":g.builder_tips_usd.sum(),
            "estimated_pnl_usd":g.pnl_usd.sum(),
            "median_trade_revenue_usd":g.mr_usd.median(),
            "median_trade_pnl_usd":g.pnl_usd.median(),
            "median_profit_margin":margins.median() if not margins.empty else None,
            "trades":len(g),
        })
    return pd.DataFrame(rows).sort_values("total_volume_usd",ascending=False)
