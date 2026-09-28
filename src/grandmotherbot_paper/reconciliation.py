"""Executable reconciliation checks for the paper reference tables.

This module deliberately separates two claims:
1. reference-data integrity: the checked-in transcription is internally consistent;
2. empirical reproduction: GrandMother recomputes the paper results from raw/curated
   source data.

The second claim cannot be made from the published summary CSVs alone.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


REFERENCE_DIR = Path(__file__).resolve().parents[2] / "data" / "reference"


@dataclass(frozen=True)
class ReconciliationStatus:
    reference_integrity: bool
    empirical_reproduction: bool
    raw_dataset_available: bool
    reason: str


def load_reference(name: str) -> pd.DataFrame:
    path = REFERENCE_DIR / name
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def validate_table1() -> None:
    df = load_reference("paper_table1.csv")
    required = {
        "searcher",
        "estimated_revenue_usd",
        "builder_tips_usd",
        "estimated_pnl_usd",
    }
    missing = required - set(df.columns)
    if missing:
        raise AssertionError(f"table 1 missing columns: {sorted(missing)}")
    delta = (
        df["estimated_revenue_usd"]
        - df["builder_tips_usd"]
        - df["estimated_pnl_usd"]
    ).abs()
    if (delta > 1.0).any():
        raise AssertionError("table 1 PnL arithmetic does not reconcile within $1")


def validate_table2() -> None:
    df = load_reference("paper_table2.csv")
    required = {
        "builder_profit_usd",
        "searcher_pnl_usd",
        "aggregated_profit_usd",
    }
    missing = required - set(df.columns)
    if missing:
        raise AssertionError(f"table 2 missing columns: {sorted(missing)}")
    expected = df["builder_profit_usd"] + df["searcher_pnl_usd"].fillna(0)
    if (expected - df["aggregated_profit_usd"]).abs().gt(1.0).any():
        raise AssertionError("table 2 aggregate profit does not reconcile within $1")


def validate_table9() -> None:
    df = load_reference("paper_table9.csv")
    required = {
        "total_trades",
        "inventory_adjustment_trades",
        "arbitrage_trades",
        "profitable_trades",
        "unprofitable_trades",
    }
    missing = required - set(df.columns)
    if missing:
        raise AssertionError(f"table 9 missing columns: {sorted(missing)}")
    if (
        df["inventory_adjustment_trades"] + df["arbitrage_trades"]
        != df["total_trades"]
    ).any():
        raise AssertionError("table 9 total-trade decomposition failed")
    if (
        df["profitable_trades"] + df["unprofitable_trades"]
        != df["arbitrage_trades"]
    ).any():
        raise AssertionError("table 9 profitable/unprofitable decomposition failed")


def validate_profiles() -> None:
    profiles = load_reference("searcher_profiles.csv")
    labels = load_reference("searcher_labels.csv")
    if profiles["searcher"].duplicated().any():
        raise AssertionError("duplicate searcher profile")
    if labels["searcher"].duplicated().any():
        raise AssertionError("duplicate searcher label")
    if set(profiles["searcher"]) != set(labels["searcher"]):
        raise AssertionError("profile and label registries disagree")
    pattern3 = set(
        profiles.loc[profiles["pattern"] == 3, "searcher"]
    )
    expected_pattern3 = {"Bard", "Jinx", "Tristana", "Lux"}
    if pattern3 != expected_pattern3:
        raise AssertionError(
            f"pattern 3 registry mismatch: {sorted(pattern3)}"
        )


def validate_reference_tables() -> None:
    validate_table1()
    validate_table2()
    validate_table9()
    validate_profiles()


def empirical_reproduction_status() -> ReconciliationStatus:
    validate_reference_tables()

    # No raw/curated empirical transaction + Binance markout dataset is checked
    # into this repository. Summary tables are targets, not evidence of a rerun.
    raw_dataset_candidates = (
        REFERENCE_DIR / "transactions.csv",
        REFERENCE_DIR / "markouts.csv",
        REFERENCE_DIR / "empirical_dataset.parquet",
    )
    available = any(path.exists() for path in raw_dataset_candidates)
    return ReconciliationStatus(
        reference_integrity=True,
        empirical_reproduction=available,
        raw_dataset_available=available,
        reason=(
            "raw/curated empirical inputs are available"
            if available
            else "published reference tables are present, but raw/curated empirical "
            "inputs required to rerun identification, reconstruction, markouts and "
            "profitability are not present"
        ),
    )
