from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .constants import (
    HORIZONS,
    PAPER_END_BLOCK,
    PAPER_END_DATE,
    PAPER_START_BLOCK,
    PAPER_START_DATE,
)

@dataclass(frozen=True)
class SourceContract:
    name: str
    role: str
    required_for_replication: bool
    configured: bool
    location: str

SOURCE_CONTRACTS = (
    SourceContract(
        "dune_cex_dex",
        "Ethereum DEX transaction candidates and heuristic inputs",
        True,
        bool(__import__("os").environ.get("DUNE_API_KEY")),
        "Dune query 4931834 / dex.trades",
    ),
    SourceContract(
        "tardis_binance_spot",
        "Historical Binance USDT quotes used for markouts",
        True,
        bool(__import__("os").environ.get("TARDIS_API_KEY")),
        "Tardis Binance historical quotes",
    ),
    SourceContract(
        "binance_token_registry",
        "Binance-listed ERC-20 contract cross-check",
        True,
        False,
        "Normalized cex_tokens.csv",
    ),
    SourceContract(
        "relay_builder_data",
        "MEV-Boost winning-builder / bid data",
        True,
        False,
        "Normalized builder_blocks.csv",
    ),
    SourceContract(
        "ultrasound_adjustments",
        "Builder bid adjustment / refund correction",
        True,
        False,
        "Normalized builder_blocks.csv",
    ),
)

REQUIRED_INPUTS = {
    "transactions.csv": "Dune-derived candidate transactions",
    "swaps.csv": "DEX swap logs used for multi-swap reconstruction",
    "markouts.csv": "Tardis Binance USDT mid-price observations",
    "builder_blocks.csv": "Builder profitability and bid-adjustment inputs",
    "cex_tokens.csv": "Binance-listed ERC-20 contract registry",
}

def paper_contract() -> dict:
    return {
        "paper_period": {
            "start_block": PAPER_START_BLOCK,
            "end_block": PAPER_END_BLOCK,
            "start_date": PAPER_START_DATE,
            "end_date": PAPER_END_DATE,
        },
        "markout_horizons_s": [str(h) for h in HORIZONS],
        "required_inputs": REQUIRED_INPUTS,
        "source_contracts": [
            {
                "name": s.name,
                "role": s.role,
                "required_for_replication": s.required_for_replication,
                "configured": s.configured,
                "location": s.location,
            }
            for s in SOURCE_CONTRACTS
        ],
    }

def input_readiness(root: str | Path = "data/input") -> dict:
    path = Path(root)
    files = {
        filename: {
            "present": (path / filename).is_file(),
            "role": role,
        }
        for filename, role in REQUIRED_INPUTS.items()
    }
    return {
        "ready": all(item["present"] for item in files.values()),
        "files": files,
    }
