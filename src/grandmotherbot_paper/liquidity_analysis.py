from __future__ import annotations
from decimal import Decimal
import pandas as pd
from .correlation import spearman
from .liquidity import pair_class

def searcher_liquidity_mix(df: pd.DataFrame) -> pd.DataFrame:
    w=df.copy()
    w["pair_class"]=[pair_class(a,b) for a,b in zip(w.token_a,w.token_b)]
    rows=[]
    for label,g in w.groupby("searcher_label"):
        total=len(g); total_vol=g.volume_usd.sum()
        for cls in ["Major-Major","Major-ALT","ALT-ALT"]:
            x=g[g.pair_class==cls]
            rows.append({
                "searcher_label":label,
                "pair_class":cls,
                "trade_count":len(x),
                "trade_count_share":len(x)/total if total else 0,
                "volume_usd":x.volume_usd.sum(),
                "volume_share":x.volume_usd.sum()/total_vol if total_vol else 0,
            })
    return pd.DataFrame(rows)

def post_peak_decline(curve: dict[Decimal,Decimal]) -> Decimal | None:
    if not curve:
        return None
    peak_h=max(curve,key=curve.get)
    peak=curve[peak_h]
    if peak==0:
        return None
    target=peak_h+Decimal("3.0")
    later=[(h,v) for h,v in curve.items() if h>=target]
    if not later:
        return None
    h=min(later,key=lambda x:x[0])[0]
    return (peak-curve[h])/abs(peak)

def major_major_correlation(major_major_share: pd.Series, decline: pd.Series) -> float:
    return spearman(major_major_share.tolist(),decline.tolist())
