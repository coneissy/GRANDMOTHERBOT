from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SourceRun:
    """Immutable provenance record for one external research-data retrieval."""

    source: str
    query_id: str | None
    exchange: str | None
    requested_from: str
    requested_to: str
    retrieved_at: str
    rows_received: int
    rows_accepted: int
    rows_rejected: int
    stale_rows: int = 0
    missing_timestamp_rows: int = 0
    schema_version: str = "1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def source_run(
    *,
    source: str,
    requested_from: str,
    requested_to: str,
    rows_received: int,
    rows_accepted: int,
    rows_rejected: int,
    query_id: str | None = None,
    exchange: str | None = None,
    stale_rows: int = 0,
    missing_timestamp_rows: int = 0,
    schema_version: str = "1",
) -> SourceRun:
    values = {
        "rows_received": rows_received,
        "rows_accepted": rows_accepted,
        "rows_rejected": rows_rejected,
        "stale_rows": stale_rows,
        "missing_timestamp_rows": missing_timestamp_rows,
    }
    if any(v < 0 for v in values.values()):
        raise ValueError("provenance counts cannot be negative")
    if rows_accepted + rows_rejected != rows_received:
        raise ValueError("accepted + rejected must equal received")
    return SourceRun(
        source=source,
        query_id=query_id,
        exchange=exchange,
        requested_from=requested_from,
        requested_to=requested_to,
        retrieved_at=utc_now(),
        **values,
        schema_version=schema_version,
    )


def write_manifest(path: str | Path, runs: list[SourceRun]) -> str:
    """Write deterministic JSON provenance and return its SHA-256."""
    payload = {
        "manifest_version": "1",
        "runs": [asdict(run) for run in runs],
    }
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    digest = hashlib.sha256(encoded).hexdigest()
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(encoded)
    return digest
