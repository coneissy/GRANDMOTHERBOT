from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import pandas as pd
@dataclass(frozen=True)
class SourceSpec:
    name:str; source_type:str; provenance:str; methodology_version:str

def read_normalized_csv(path:str|Path,required:tuple[str,...])->pd.DataFrame:
    df=pd.read_csv(path)
    missing=set(required)-set(df.columns)
    if missing: raise ValueError("missing columns: "+", ".join(sorted(missing)))
    return df

DEX_SOURCE=SourceSpec("dune.dex.trades","historical","Dune dex.trades","paper-2507.13023v3")
CEX_SOURCE=SourceSpec("binance-historical","historical","Tardis.dev","paper-2507.13023v3")
BUILDER_SOURCE=SourceSpec("mev-boost","historical","relayscan.io","paper-2507.13023v3")
ULTRA_SOURCE=SourceSpec("ultra-sound","historical","Ultra Sound relay API","paper-2507.13023v3")
