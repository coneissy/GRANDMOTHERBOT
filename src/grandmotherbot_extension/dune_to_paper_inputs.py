from __future__ import annotations

"""Deterministic bridge from captured Dune rows to frozen paper input tables.

This is an ingestion adapter, not a new identification methodology. Every H1-H6
input must be explicitly present in the source row. Missing evidence is rejected
rather than guessed. Manual exclusions are applied by the existing paper
identifier.
"""

import json
from pathlib import Path
from typing import Any

import pandas as pd

from grandmotherbot_paper.identification import CandidateTransaction, classify_transaction

TX_COLUMNS = [
    "tx_hash", "block_number", "slot_time", "from_address",
    "observed_public_mempool", "first_swap_in_pool_direction", "atomic_mev",
    "liquidation", "ofa_backrun", "known_router", "labeled_trading_bot",
    "ens_named_eoa_controller", "erc721_transfer", "final_pair_major_cex_listed",
    "searcher_label", "builder",
]
SWAP_COLUMNS = [
    "tx_hash", "log_index", "dex", "pool", "token_in", "token_out",
    "amount_in", "amount_out",
]

ALIASES = {
    "tx_hash": ("tx_hash", "transaction_hash"),
    "block_number": ("block_number",),
    "slot_time": ("slot_time", "block_time"),
    "from_address": ("from_address", "tx_from"),
    "observed_public_mempool": ("observed_public_mempool",),
    "first_swap_in_pool_direction": ("first_swap_in_pool_direction",),
    "atomic_mev": ("atomic_mev",),
    "liquidation": ("liquidation",),
    "ofa_backrun": ("ofa_backrun",),
    "known_router": ("known_router",),
    "labeled_trading_bot": ("labeled_trading_bot",),
    "ens_named_eoa_controller": ("ens_named_eoa_controller",),
    "erc721_transfer": ("erc721_transfer",),
    "final_pair_major_cex_listed": ("final_pair_major_cex_listed",),
    "searcher_label": ("searcher_label",),
    "builder": ("builder",),
}


def _rows_from_json(path: str | Path) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        for key in ("rows", "result", "data"):
            value = payload.get(key)
            if isinstance(value, dict) and isinstance(value.get("rows"), list):
                return value["rows"]
            if isinstance(value, list):
                return value
    if isinstance(payload, list):
        return payload
    raise ValueError("Dune capture does not contain a row list")


def _value(row: dict[str, Any], name: str) -> Any:
    for key in ALIASES[name]:
        if key in row:
            return row[key]
    raise ValueError(f"Dune row missing required evidence column: {name}")


def _bool(row: dict[str, Any], name: str) -> bool:
    value = _value(row, name)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str) and value.strip().lower() in {"true", "false"}:
        return value.strip().lower() == "true"
    raise ValueError(f"{name}: expected boolean, got {value!r}")


def identify_rows(rows: list[dict[str, Any]]) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    transactions: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []

    for row in rows:
        candidate = CandidateTransaction(
            observed_public_mempool=_bool(row, "observed_public_mempool"),
            first_swap_in_pool_direction=_bool(row, "first_swap_in_pool_direction"),
            atomic_mev=_bool(row, "atomic_mev"),
            liquidation=_bool(row, "liquidation"),
            ofa_backrun=_bool(row, "ofa_backrun"),
            known_router=_bool(row, "known_router"),
            labeled_trading_bot=_bool(row, "labeled_trading_bot"),
            ens_named_eoa_controller=_bool(row, "ens_named_eoa_controller"),
            erc721_transfer=_bool(row, "erc721_transfer"),
            final_pair_major_cex_listed=_bool(row, "final_pair_major_cex_listed"),
            from_address=str(_value(row, "from_address")),
        )
        output = {name: _value(row, name) if name not in {
            "observed_public_mempool", "first_swap_in_pool_direction",
            "atomic_mev", "liquidation", "ofa_backrun", "known_router",
            "labeled_trading_bot", "ens_named_eoa_controller", "erc721_transfer",
            "final_pair_major_cex_listed"
        } else _bool(row, name) for name in TX_COLUMNS if name in row or name in ALIASES}
        output["tx_hash"] = _value(row, "tx_hash")
        output["block_number"] = _value(row, "block_number")
        output["slot_time"] = _value(row, "slot_time")
        output["from_address"] = _value(row, "from_address")

        if classify_transaction(candidate) == "candidate_cex_dex":
            transactions.append(output)
        else:
            excluded.append({"tx_hash": output["tx_hash"], "reason": "paper_heuristic_or_manual_exclusion"})

    return pd.DataFrame(transactions, columns=TX_COLUMNS), excluded


def extract_swaps(rows: list[dict[str, Any]], accepted_hashes: set[str]) -> pd.DataFrame:
    records = []
    for row in rows:
        tx_hash = str(row.get("tx_hash", row.get("transaction_hash", "")))
        if tx_hash not in accepted_hashes:
            continue
        if not all(key in row for key in ("log_index", "token_in", "token_out", "amount_in", "amount_out")):
            raise ValueError("Dune swap row missing log_index/token_in/token_out/amount_in/amount_out")
        records.append({key: row.get(key) for key in SWAP_COLUMNS})
    return pd.DataFrame(records, columns=SWAP_COLUMNS)


def build_paper_inputs(raw_path: str | Path, output_dir: str | Path) -> dict[str, int]:
    rows = _rows_from_json(raw_path)
    tx, excluded = identify_rows(rows)
    swaps = extract_swaps(rows, set(tx["tx_hash"].astype(str))) if not tx.empty else pd.DataFrame(columns=SWAP_COLUMNS)

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    tx.to_csv(root / "transactions.csv", index=False)
    swaps.to_csv(root / "swaps.csv", index=False)
    pd.DataFrame(excluded).to_csv(root / "identification_exclusions.csv", index=False)

    return {
        "source_rows": len(rows),
        "transactions": len(tx),
        "swaps": len(swaps),
        "excluded": len(excluded),
    }
