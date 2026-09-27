from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Iterable

import pandas as pd

from .io import SWAP_COLUMNS, TRANSACTION_COLUMNS, require_columns
from .reconstruction import EffectiveTrade, Swap, reconstruct_effective_trade


RECONSTRUCTION_REASON_OK = "reconstructed"
RECONSTRUCTION_REASON_NO_SWAPS = "no_swap_legs"
RECONSTRUCTION_REASON_INVALID_SWAPS = "invalid_swap_legs"


def _decimal(value: object, field: str) -> Decimal:
    if value is None or pd.isna(value):
        raise ValueError(f"{field} must be non-null")
    try:
        value_decimal = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not value_decimal.is_finite() or value_decimal <= 0:
        raise ValueError(f"{field} must be finite and positive")
    return value_decimal


def normalize_dune_transactions(rows: Iterable[dict]) -> pd.DataFrame:
    """Normalize curated Dune rows without changing identification semantics."""
    frame = pd.DataFrame(list(rows))
    require_columns(frame, TRANSACTION_COLUMNS, "dune_transactions")
    if frame["tx_hash"].isna().any() or frame["tx_hash"].astype(str).str.strip().eq("").any():
        raise ValueError("dune_transactions: tx_hash must be non-empty")
    if frame["tx_hash"].duplicated().any():
        raise ValueError("dune_transactions: duplicate tx_hash values are not allowed")
    return frame.loc[:, TRANSACTION_COLUMNS].copy()


def _swap_legs(group: pd.DataFrame) -> tuple[Swap, ...]:
    legs: list[Swap] = []
    for row in group.sort_values("log_index").itertuples(index=False):
        if pd.isna(row.token_in) or pd.isna(row.token_out):
            raise ValueError("swap token addresses must be non-null")
        token_in = str(row.token_in).strip()
        token_out = str(row.token_out).strip()
        if not token_in or not token_out:
            raise ValueError("swap token addresses must be non-empty")
        legs.append(
            Swap(
                token_in=token_in,
                token_out=token_out,
                amount_in=_decimal(row.amount_in, "amount_in"),
                amount_out=_decimal(row.amount_out, "amount_out"),
                log_index=int(row.log_index),
            )
        )
    return tuple(legs)


def reconstruct_dune_transactions(
    transactions: pd.DataFrame,
    swaps: pd.DataFrame,
) -> pd.DataFrame:
    """Reconstruct candidates with explicit, auditable reconstruction outcomes.

    Identification stays upstream. Missing or invalid swap evidence is recorded
    as a reconstruction outcome rather than silently deleting the candidate.
    """
    require_columns(transactions, TRANSACTION_COLUMNS, "transactions")
    require_columns(swaps, SWAP_COLUMNS, "swaps")

    if transactions["tx_hash"].duplicated().any():
        raise ValueError("transactions: duplicate tx_hash values are not allowed")
    if swaps["tx_hash"].isna().any() or swaps["tx_hash"].astype(str).str.strip().eq("").any():
        raise ValueError("swaps: tx_hash must be non-empty")

    known_hashes = set(transactions["tx_hash"].astype(str))
    unknown = set(swaps["tx_hash"].astype(str)) - known_hashes
    if unknown:
        raise ValueError(f"swaps: unknown tx_hash {sorted(unknown)[0]}")

    rows: list[dict] = []
    for tx_hash, tx_row in transactions.set_index("tx_hash").iterrows():
        group = swaps[swaps["tx_hash"].astype(str) == str(tx_hash)]
        if group.empty:
            rows.append({
                "tx_hash": str(tx_hash),
                "reconstruction_status": RECONSTRUCTION_REASON_NO_SWAPS,
            })
            continue

        try:
            trade: EffectiveTrade = reconstruct_effective_trade(_swap_legs(group))
        except (ValueError, InvalidOperation) as exc:
            rows.append({
                "tx_hash": str(tx_hash),
                "reconstruction_status": f"{RECONSTRUCTION_REASON_INVALID_SWAPS}: {exc}",
            })
            continue

        rows.append({
            "tx_hash": str(tx_hash),
            "block_number": tx_row["block_number"],
            "slot_time": tx_row["slot_time"],
            "searcher_label": tx_row["searcher_label"],
            "volume_usd": tx_row["volume_usd"],
            "token_bought_contract": trade.token_bought,
            "token_bought_amount": trade.amount_bought,
            "token_sold_contract": trade.token_sold,
            "token_sold_amount": trade.amount_sold,
            "reconstruction_status": RECONSTRUCTION_REASON_OK,
        })

    columns = [
        "tx_hash", "block_number", "slot_time", "searcher_label", "volume_usd",
        "token_bought_contract", "token_bought_amount",
        "token_sold_contract", "token_sold_amount", "reconstruction_status",
    ]
    return pd.DataFrame(rows, columns=columns)
