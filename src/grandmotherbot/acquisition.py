from __future__ import annotations

"""Authenticated acquisition adapters for the historical replication inputs.

No credentials are embedded. The adapters fail closed when an entitled source
is not configured, rather than silently substituting another dataset.
"""

import os
from pathlib import Path
from typing import Any

import requests


class AcquisitionError(RuntimeError):
    pass


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise AcquisitionError(f"{name} is required for this source")
    return value


def download_dune_query(
    query_id: int = 4_931_834,
    output: str | Path = "data/raw/dune_4931834.json",
    *,
    limit: int = 100_000,
) -> Path:
    """Download the complete latest Dune result using bounded pagination.

    Dune exposes ``limit`` and ``offset`` pagination on the latest-result
    endpoint. We preserve the query result as one normalized envelope and fail
    closed if the server returns an unexpected page shape.
    """
    if limit <= 0:
        raise ValueError("limit must be positive")

    api_key = _require_env("DUNE_API_KEY")
    url = f"https://api.dune.com/api/v1/query/{query_id}/results"
    headers = {"X-DUNE-API-KEY": api_key, "Accept": "application/json"}

    rows: list[dict[str, Any]] = []
    offset = 0
    first_payload: dict[str, Any] | None = None

    while True:
        response = requests.get(
            url, headers=headers, params={"limit": limit, "offset": offset}, timeout=60
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        result = payload.get("result")
        page = result.get("rows") if isinstance(result, dict) else None
        if not isinstance(page, list):
            raise AcquisitionError(
                f"Dune response did not contain a result.rows list at offset {offset}"
            )
        if first_payload is None:
            first_payload = payload
        rows.extend(page)
        if len(page) < limit:
            break
        next_offset = payload.get("next_offset")
        offset = int(next_offset) if next_offset is not None else offset + len(page)
        if offset <= 0:
            raise AcquisitionError("Dune pagination returned a non-progressing offset")

    if first_payload is None:
        raise AcquisitionError("Dune returned no result pages")
    combined = dict(first_payload)
    combined_result = dict(combined.get("result", {}))
    combined_result["rows"] = rows
    metadata = combined_result.get("metadata")
    if isinstance(metadata, dict):
        combined_metadata = dict(metadata)
        combined_metadata["row_count"] = len(rows)
        combined_metadata["total_row_count"] = len(rows)
        combined_result["metadata"] = combined_metadata
    combined["result"] = combined_result
    combined["pagination"] = {
        "page_size": limit, "pages": (len(rows) + limit - 1) // limit, "row_count": len(rows)
    }
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(__import__("json").dumps(combined, separators=(",", ":")), encoding="utf-8")
    return destination


def download_tardis_minute(
    *,
    day: str,
    minute_offset: int,
    filters_json: str,
    output: str | Path,
) -> Path:
    """Download one exact Binance historical minute from Tardis.

    Tardis HTTP replay is minute-sliced. A full paper replication must iterate
    the complete sample and preserve every raw response before normalization.
    """
    api_key = _require_env("TARDIS_API_KEY")
    url = "https://api.tardis.dev/v1/data-feeds/binance"
    response = requests.get(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept-Encoding": "gzip",
        },
        params={
            "from": day,
            "offset": minute_offset,
            "filters": filters_json,
        },
        timeout=60,
    )
    response.raise_for_status()

    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(response.content)
    return destination
