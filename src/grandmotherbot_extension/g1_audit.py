from __future__ import annotations

"""G1 source audit for the locked Dune query.

This module is deliberately read-only with respect to PAPER_REPLICATION:
it captures the authenticated Dune result and writes only raw evidence plus
an audit summary. It never fabricates missing fields or populates
data/input/*.csv.
"""

import argparse
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .acquisition_pipeline import acquire_dune_query
from .source_adapters import DuneAdapter, dune_rows

QUERY_ID = 4_931_834
START_BLOCK = 17_866_488
END_BLOCK = 21_998_438
START_DATE = "2023-08-08"
END_DATE = "2025-03-08"

REQUIRED_EVIDENCE = (
    "observed_public_mempool",
    "first_swap_in_pool_direction",
    "atomic_mev",
    "liquidation",
    "ofa_backrun",
    "known_router",
    "labeled_trading_bot",
    "ens_named_eoa_controller",
    "erc721_transfer",
    "final_pair_major_cex_listed",
)

BLOCK_KEYS = ("block_number", "block_num", "block")
DATE_KEYS = ("block_time", "slot_time", "event_time", "timestamp", "time")
TX_KEYS = ("tx_hash", "transaction_hash", "hash")


def _pick(row: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in row:
            return row[key]
    return None


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _date_prefix(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text[:10] if len(text) >= 10 else None


def audit_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    columns = sorted({key for row in rows for key in row})
    block_values = [_as_int(_pick(row, BLOCK_KEYS)) for row in rows]
    date_values = [_date_prefix(_pick(row, DATE_KEYS)) for row in rows]

    in_block = [
        value is not None and START_BLOCK <= value <= END_BLOCK
        for value in block_values
    ]
    in_date = [
        value is not None and START_DATE <= value <= END_DATE
        for value in date_values
    ]

    tx_values = [_pick(row, TX_KEYS) for row in rows]
    tx_counts = Counter(str(value) for value in tx_values if value is not None)

    evidence_presence = {
        field: sum(field in row for row in rows)
        for field in REQUIRED_EVIDENCE
    }

    return {
        "query_id": QUERY_ID,
        "source_rows": len(rows),
        "column_count": len(columns),
        "columns": columns,
        "unique_tx_hashes": len({value for value in tx_values if value is not None}),
        "duplicate_tx_rows": sum(count - 1 for count in tx_counts.values() if count > 1),
        "block_field_present_rows": sum(value is not None for value in block_values),
        "date_field_present_rows": sum(value is not None for value in date_values),
        "in_paper_block_range": sum(in_block),
        "in_paper_date_range": sum(in_date),
        "required_h1_h6_evidence_presence": evidence_presence,
        "missing_required_evidence_columns": [
            field for field, count in evidence_presence.items() if count == 0
        ],
        "paper_expected_candidate_population": 8_723_233,
        "expected_population_is_not_asserted": True,
        "paper_window": {
            "start_block": START_BLOCK,
            "end_block": END_BLOCK,
            "start_date": START_DATE,
            "end_date": END_DATE,
        },
        "audited_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def run_audit(output_dir: str | Path = "data/raw/g1") -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    captured = acquire_dune_query(output=output / "dune_4931834.json")
    raw_payload = json.loads(Path(captured.output).read_text(encoding="utf-8"))
    rows = dune_rows(raw_payload)

    summary = audit_rows(rows)
    (output / "g1_audit.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the GrandMother G1 Dune source audit.")
    parser.add_argument("--output", default="data/raw/g1")
    args = parser.parse_args()

    if not os.environ.get("DUNE_API_KEY"):
        raise SystemExit("DUNE_API_KEY is required; no source data was fabricated.")

    summary = run_audit(args.output)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
