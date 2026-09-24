from __future__ import annotations

import pandas as pd

from .correlation import spearman

def daily_share(df: pd.DataFrame, value_col: str, group_col: str="searcher_label") -> pd.DataFrame:
    w=df.copy()
    w["slot_time"]=pd.to_datetime(w["slot_time"],utc=True)
    w["date"]=w["slot_time"].dt.date.astype(str)
    g=w.groupby(["date",group_col])[value_col].sum().reset_index()
    g["share"]=g.groupby("date")[value_col].transform(lambda s:s/s.sum() if s.sum() else 0)
    return g

def builder_daily_share(df: pd.DataFrame, value_col: str="volume_usd") -> pd.DataFrame:
    return daily_share(df,value_col,"builder")

def lagged_spearman(series_a: pd.Series, series_b: pd.Series, lag_days: int) -> float:
    a=series_a.copy(); b=series_b.copy()
    joined=pd.concat([a,b],axis=1).dropna()
    if lag_days:
        joined["b_lag"]=joined.iloc[:,1].shift(-lag_days)
        joined=joined.dropna()
        return spearman(joined.iloc[:,0].tolist(),joined["b_lag"].tolist())
    return spearman(joined.iloc[:,0].tolist(),joined.iloc[:,1].tolist())

def bidirectional_lag_correlations(a: pd.Series,b: pd.Series,lags=(0,1,3,7)):
    return {
        f"a_to_b_{lag}d":lagged_spearman(a,b,lag)
        for lag in lags
    } | {
        f"b_to_a_{lag}d":lagged_spearman(b,a,lag)
        for lag in lags
    }
