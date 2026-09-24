from pathlib import Path
import pandas as pd

REQUIRED_FILES = {
    "transactions": "transactions.csv",
    "swaps": "swaps.csv",
    "markouts": "markouts.csv",
    "builder_blocks": "builder_blocks.csv",
    "cex_tokens": "cex_tokens.csv",
}

def load_inputs(directory: str | Path) -> dict[str, pd.DataFrame]:
    root=Path(directory)
    result={}
    for name, filename in REQUIRED_FILES.items():
        path=root/filename
        if path.exists():
            result[name]=pd.read_csv(path)
    return result

def require_columns(df: pd.DataFrame, columns: list[str], name: str) -> None:
    missing=[c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"{name}: missing columns: {', '.join(missing)}")

def validate_inputs(inputs: dict[str,pd.DataFrame]) -> list[str]:
    errors=[]
    specs={
        "transactions":["tx_hash","block_number","slot_time","from_address"],
        "swaps":["tx_hash","log_index","token_in","token_out","amount_in","amount_out"],
        "markouts":["tx_hash","horizon_s","token_a_usdt_mid","token_b_usdt_mid","cex_taker_fees_usd","dex_volume_usd"],
        "builder_blocks":["block_number","builder","slot_time","delta_coinbase_usd","bid_value_usd","bid_adjusted","bid_adjustment_delta_usd"],
        "cex_tokens":["symbol","contract_address"],
    }
    for name, columns in specs.items():
        if name in inputs:
            try: require_columns(inputs[name],columns,name)
            except ValueError as e: errors.append(str(e))
    return errors
