from pathlib import Path

import pandas as pd

REQUIRED_FILES = {
    "transactions": "transactions.csv",
    "swaps": "swaps.csv",
    "markouts": "markouts.csv",
    "builder_blocks": "builder_blocks.csv",
    "cex_tokens": "cex_tokens.csv",
}

TRANSACTION_COLUMNS = [
    "tx_hash", "block_number", "slot_time", "from_address",
    "observed_public_mempool", "first_swap_in_pool_direction",
    "atomic_mev", "liquidation", "ofa_backrun", "known_router",
    "labeled_trading_bot", "ens_named_eoa_controller", "erc721_transfer",
    "final_pair_major_cex_listed", "searcher_label", "volume_usd",
]
SWAP_COLUMNS = [
    "tx_hash", "log_index", "token_in", "token_out", "amount_in", "amount_out",
]
MARKOUT_COLUMNS = [
    "tx_hash", "horizon_s", "amount_a", "amount_b", "token_a_usdt_mid",
    "token_b_usdt_mid", "cex_taker_fees_usd", "dex_volume_usd", "base_fees_usd",
    "builder_tips_usd", "searcher_label",
]
BUILDER_COLUMNS = [
    "block_number", "builder", "slot_time", "bid_adjusted",
]
BUILDER_USD_COLUMNS = ["delta_coinbase_usd", "bid_value_usd", "bid_adjustment_delta_usd"]
BUILDER_ETH_COLUMNS = ["delta_coinbase_eth", "bid_value_eth", "bid_adjustment_delta_eth", "eth_usdt_mid"]
CEX_TOKEN_COLUMNS = ["symbol", "contract_address"]


def load_inputs(directory: str | Path) -> dict[str, pd.DataFrame]:
    root = Path(directory)
    result = {}
    for name, filename in REQUIRED_FILES.items():
        path = root / filename
        if path.exists():
            result[name] = pd.read_csv(path)
    return result


def require_columns(df: pd.DataFrame, columns: list[str], name: str) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"{name}: missing columns: {', '.join(missing)}")


def validate_inputs(inputs: dict[str, pd.DataFrame]) -> list[str]:
    errors = []
    specs = {
        "transactions": TRANSACTION_COLUMNS,
        "swaps": SWAP_COLUMNS,
        "markouts": MARKOUT_COLUMNS,
        "builder_blocks": BUILDER_COLUMNS,
        "cex_tokens": CEX_TOKEN_COLUMNS,
    }
    for name, columns in specs.items():
        if name not in inputs:
            errors.append(f"{name}: required input file is missing")
            continue
        try:
            require_columns(inputs[name], columns, name)
        except ValueError as exc:
            errors.append(str(exc))

    if "builder_blocks" in inputs:
        builder = inputs["builder_blocks"]
        has_usd = all(c in builder.columns for c in BUILDER_USD_COLUMNS)
        has_eth = all(c in builder.columns for c in BUILDER_ETH_COLUMNS)
        if not (has_usd or has_eth):
            errors.append(
                "builder_blocks: must contain either the complete USD fee set "
                "or the complete ETH fee set"
            )
    return errors
