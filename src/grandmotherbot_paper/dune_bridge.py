from __future__ import annotations

from decimal import Decimal
from typing import Iterable

import pandas as pd

from .reconstruction import Swap, EffectiveTrade, reconstruct_effective_trade
from .io import TRANSACTION_COLUMNS, SWAP_COLUMNS, require_columns


def normalize_dune_transactions(rows: Iterable[dict]) -> pd.DataFrame:
    """Normalize Dune query rows without changing identification semantics."""
    frame = pd.DataFrame(list(rows))
    require_columns(frame, TRANSACTION_COLUMNS, "dune_transactions")
    if frame["tx_hash"].isna().any() or frame["tx_hash"].astype(str).str.strip().eq("").any():
        raise ValueError("dune_transactions: tx_hash must be non-empty")
    if frame["tx_hash"].duplicated().any():
        raise ValueError("dune_transactions: duplicate tx_hash values are not allowed")
    return frame.loc[:, TRANSACTION_COLUMNS].copy()


def reconstruct_dune_transactions(
    transactions: pd.DataFrame,
    swaps: pd.DataFrame,
) -> pd.DataFrame:
    """Join curated transactions to DEX swap legs and reconstruct net trades."""
    require_columns(transactions, TRANSACTION_COLUMNS, "transactions")
    require_columns(swaps, SWAP_COLUMNS, "swaps")

    if transactions["tx_hash"].duplicated().any():
        raise ValueError("transactions: duplicate tx_hash values are not allowed")
    if swaps["tx_hash"].isna().any():
        raise ValueError("swaps: tx_hash must be non-null")

    known_hashes = set(transactions["tx_hash"].astype(str))
    rows: list[dict] = []
    for tx_hash, group in swaps.groupby("tx_hash", sort=False):
        tx_hash = str(tx_hash)
        if tx_hash not in known_hashes:
            raise ValueError(f"swaps: unknown tx_hash {tx_hash}")
        legs = tuple(
            Swap(
                token_in=str(row.token_in),
                token_out=str(row.token_out),
                amount_in=Decimal(str(row.amount_in)),
                amount_out=Decimal(str(row.amount_out)),
                log_index=int(row.log_index),
            )
            for row in group.sort_values("log_index").itertuples(index=False)
        )
        trade: EffectiveTrade = reconstruct_effective_trade(legs)
        rows.append({
            "tx_hash": tx_hash,
            "token_bought_contract": trade.token_bought,
            "token_bought_amount": trade.amount_bought,
            "token_sold_contract": trade.token_sold,
            "token_sold_amount": trade.amount_sold,
        })

    result = pd.DataFrame(rows)
    if result.empty:
        return pd.DataFrame(
            columns=[
                "tx_hash", "token_bought_contract", "token_bought_amount",
                "token_sold_contract", "token_sold_amount",
            ]
        )

    result = transactions[["tx_hash", "block_number", "slot_time", "searcher_label", "volume_usd"]].merge(
        result, on="tx_hash", how="inner", validate="one_to_one"
    )
    if len(result) != len(result["tx_hash"].unique()):
        raise ValueError("reconstructed trades must remain one row per transaction")
    return result
