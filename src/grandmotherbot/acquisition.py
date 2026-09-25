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
    """Download a Dune query result using the official API.

    The query itself is frozen by ID. Pagination/export strategy can be
    extended without changing the paper specification.
    """
    api_key = _require_env("DUNE_API_KEY")
    url = f"https://api.dune.com/api/v2/query/{query_id}/results"
    response = requests.get(
        url,
        headers={"X-Dune-API-Key": api_key, "Accept": "application/json"},
        params={"limit": limit},
        timeout=60,
    )
    response.raise_for_status()
    payload: dict[str, Any] = response.json()
    rows = payload.get("result", {}).get("rows")
    if rows is None:
        raise AcquisitionError("Dune response did not contain result.rows")

    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        __import__("json").dumps(payload, separators=(",", ":")),
        encoding="utf-8",
    )
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
