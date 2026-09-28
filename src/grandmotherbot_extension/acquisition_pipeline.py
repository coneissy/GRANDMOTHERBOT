from __future__ import annotations

"""Controlled acquisition of paper-specified raw sources.

This module deliberately stops before PAPER_REPLICATION normalization. Raw
source material is written under data/raw and accompanied by a provenance
manifest. It never fabricates or overwrites data/input/*.csv.
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .source_adapters import DuneAdapter, TardisAdapter
from .provenance import SourceRun, write_manifest


@dataclass(frozen=True)
class AcquisitionResult:
    source: str
    output: str
    rows_received: int
    retrieved_at: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def acquire_dune_query(
    *,
    output: str | Path = "data/raw/dune_4931834.json",
    max_age_hours: int | None = None,
) -> AcquisitionResult:
    """Capture the locked Dune query result without transforming its rows."""
    destination = Path(output)
    retrieved_at = _now()
    result = DuneAdapter().run(max_age_hours=max_age_hours)
    rows = [
        row for row in __import__("grandmotherbot_extension.source_adapters",
                                  fromlist=["dune_rows"]).dune_rows(result)
    ]

    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = result
    if hasattr(payload, "result"):
        payload = payload.result
    if hasattr(payload, "to_dict"):
        payload = payload.to_dict()
    elif not isinstance(payload, (dict, list, tuple, str, int, float, bool, type(None))):
        payload = {"repr": repr(payload)}
    destination.write_text(
        json.dumps(payload, default=str, separators=(",", ":")),
        encoding="utf-8",
    )

    manifest = SourceRun(
        source="dune",
        query_id=4_931_834,
        exchange=None,
        requested_from=None,
        requested_to=None,
        retrieved_at=retrieved_at,
        rows_received=len(rows),
        rows_accepted=len(rows),
        rows_rejected=0,
        stale_rows=0,
        missing_timestamp_rows=0,
        schema_version="raw-dune-v1",
    )
    write_manifest(manifest, destination.with_suffix(".manifest.json"))
    return AcquisitionResult("dune", str(destination), len(rows), retrieved_at)


def acquire_tardis_minutes(
    *,
    start_iso: str,
    minutes: int,
    output_dir: str | Path = "data/raw/tardis/binance",
    channels: tuple[str, ...] = ("bookTicker", "trade"),
    symbols: tuple[str, ...] = (),
) -> list[AcquisitionResult]:
    """Capture an exact contiguous Tardis minute window.

    Each minute is persisted independently so a failed minute can be retried
    without replacing successful captures. Tardis disconnect markers remain
    in the raw NDJSON envelope.
    """
    if minutes < 1:
        raise ValueError("minutes must be >= 1")

    destination_dir = Path(output_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    adapter = TardisAdapter()
    results: list[AcquisitionResult] = []

    # Tardis's offset is the documented minute selector. Keep start_iso as
    # supplied so the caller controls the exact UTC source window.
    for offset in range(minutes):
        retrieved_at = _now()
        events = adapter.fetch_minute(
            from_iso=start_iso,
            offset_minutes=offset,
            channels=channels,
            symbols=symbols,
        )
        destination = destination_dir / f"minute_{offset:06d}.ndjson"
        with destination.open("w", encoding="utf-8") as handle:
            for event in events:
                handle.write(json.dumps(event, separators=(",", ":"), default=str))
                handle.write("\n")

        manifest = SourceRun(
            source="tardis",
            query_id=None,
            exchange="binance",
            requested_from=start_iso,
            requested_to=f"offset:{offset}",
            retrieved_at=retrieved_at,
            rows_received=len(events),
            rows_accepted=len(events),
            rows_rejected=0,
            stale_rows=0,
            missing_timestamp_rows=sum(1 for e in events if not e.get("disconnect") and not e.get("capture_time")),
            schema_version="tardis-raw-envelope-v1",
        )
        write_manifest(manifest, destination.with_suffix(".manifest.json"))
        results.append(AcquisitionResult("tardis", str(destination), len(events), retrieved_at))

    return results


def acquisition_summary(results: list[AcquisitionResult]) -> dict[str, Any]:
    return {
        "results": [asdict(result) for result in results],
        "total_rows_received": sum(result.rows_received for result in results),
    }
