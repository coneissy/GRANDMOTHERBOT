from __future__ import annotations

from pathlib import Path
import pandas as pd

def compare_to_paper_table1(computed: pd.DataFrame, reference_path: str) -> pd.DataFrame:
    ref=pd.read_csv(reference_path)
    merged=ref.merge(computed,on="searcher",how="left",suffixes=("_paper","_computed"))
    numeric=["total_volume_usd","estimated_revenue_usd","builder_tips_usd","estimated_pnl_usd"]
    for c in numeric:
        if c+"_paper" in merged and c+"_computed" in merged:
            merged[c+"_absolute_error"]=merged[c+"_computed"]-merged[c+"_paper"]
    return merged

def load_reference_tables(reference_dir: str | Path) -> dict[str,pd.DataFrame]:
    root=Path(reference_dir)
    return {
        "table1":pd.read_csv(root/"paper_table1.csv"),
        "table2":pd.read_csv(root/"paper_table2.csv"),
        "table3":pd.read_csv(root/"paper_table3.csv"),
    }
