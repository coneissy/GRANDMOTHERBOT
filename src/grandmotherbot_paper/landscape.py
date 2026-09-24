from __future__ import annotations

import pandas as pd

from .concentration import hhi

def daily_counts_and_volume(df: pd.DataFrame) -> pd.DataFrame:
    w=df.copy()
    w["slot_time"]=pd.to_datetime(w["slot_time"],utc=True)
    w["date"]=w["slot_time"].dt.date.astype(str)
    out=w.groupby("date").agg(transaction_count=("tx_hash","count"),volume_usd=("volume_usd","sum")).reset_index()
    return out

def weekly_searcher_volume(df: pd.DataFrame) -> pd.DataFrame:
    w=df.copy()
    w["slot_time"]=pd.to_datetime(w["slot_time"],utc=True)
    w["week"]=w["slot_time"].dt.to_period("W").astype(str)
    out=w.groupby(["week","searcher_label"]).agg(volume_usd=("volume_usd","sum"),trade_count=("tx_hash","count")).reset_index()
    out["share"]=out.groupby("week")["volume_usd"].transform(lambda s:s/s.sum() if s.sum() else 0)
    return out

def weekly_hhi(df: pd.DataFrame, value_col: str="volume_usd") -> pd.DataFrame:
    w=df.copy()
    w["slot_time"]=pd.to_datetime(w["slot_time"],utc=True)
    w["week"]=w["slot_time"].dt.to_period("W").astype(str)
    rows=[]
    for week,g in w.groupby("week"):
        by=g.groupby("searcher_label")[value_col].sum().tolist()
        rows.append({"week":week,"hhi":hhi(by)})
    return pd.DataFrame(rows)

def builder_weekly_share(df: pd.DataFrame, top_n: int=20) -> pd.DataFrame:
    w=df.copy()
    w["slot_time"]=pd.to_datetime(w["slot_time"],utc=True)
    w["week"]=w["slot_time"].dt.to_period("W").astype(str)
    totals=w.groupby("builder")["volume_usd"].sum().sort_values(ascending=False)
    keep=set(totals.head(top_n).index)
    w=w[w["builder"].isin(keep)]
    return w.groupby(["week","builder"])["volume_usd"].sum().reset_index()
