from __future__ import annotations

import gzip
import io
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import requests


@dataclass(frozen=True)
class DuneConfig:
    query_id: int = 4_931_834
    api_key_env: str = "DUNE_API_KEY"


@dataclass(frozen=True)
class TardisConfig:
    exchange: str = "binance"
    api_key_env: str = "TARDIS_API_KEY"


class MissingCredential(RuntimeError):
    pass


def _credential(env_name: str) -> str:
    value = os.getenv(env_name)
    if not value:
        raise MissingCredential(f"Missing required environment variable: {env_name}")
    return value


class DuneAdapter:
    """Research-source adapter. It never writes into PAPER_REPLICATION inputs."""

    def __init__(self, config: DuneConfig = DuneConfig()):
        self.config = config

    def latest_result(self) -> Any:
        from dune_client.client import DuneClient

        api_key = _credential(self.config.api_key_env)
        client = DuneClient(api_key)
        return client.get_latest_result(self.config.query_id)

    def run(self, *, max_age_hours: int | None = None) -> Any:
        from dune_client.client import DuneClient
        from dune_client.query import QueryBase

        api_key = _credential(self.config.api_key_env)
        client = DuneClient(api_key)
        query = QueryBase(name="GrandMother CEX-DEX source query",
                          query_id=self.config.query_id)
        if max_age_hours is not None:
            return client.get_latest_result(
                self.config.query_id, max_age_hours=max_age_hours
            )
        return client.run_query(query)


class TardisAdapter:
    """Historical Binance Spot raw-feed adapter.

    Raw exchange-native events are preserved. Normalization belongs downstream.
    """

    BASE_URL = "https://api.tardis.dev/v1"

    def __init__(self, config: TardisConfig = TardisConfig()):
        self.config = config

    def fetch_minute(
        self,
        *,
        from_iso: str,
        offset_minutes: int = 0,
        channels: tuple[str, ...] = ("bookTicker", "trade"),
        symbols: tuple[str, ...] = (),
    ) -> list[dict[str, Any]]:
        api_key = _credential(self.config.api_key_env)
        filters = [{
            "channel": channel,
            **({"symbols": list(symbols)} if symbols else {}),
        } for channel in channels]
        params = {
            "from": from_iso,
            "offset": offset_minutes,
            "filters": json.dumps(filters, separators=(",", ":")),
        }
        response = requests.get(
            f"{self.BASE_URL}/data-feeds/{self.config.exchange}",
            params=params,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept-Encoding": "gzip",
            },
            timeout=60,
        )
        response.raise_for_status()
        payload = response.content
        if response.headers.get("Content-Encoding", "").lower() == "gzip":
            payload = gzip.decompress(payload)
        events = []
        for line in io.BytesIO(payload).read().splitlines():
            if not line.strip():
                continue
            local_ts, raw = line.split(maxsplit=1)
            message = json.loads(raw)
            events.append({
                "capture_time": local_ts,
                "message": message,
            })
        return events


def parse_tardis_events(events: list[dict[str, Any]]) -> pd.DataFrame:
    """Flatten the adapter envelope without inventing exchange fields."""
    rows = []
    for event in events:
        rows.append({
            "capture_time": event["capture_time"],
            "message": event["message"],
        })
    return pd.DataFrame(rows, columns=["capture_time", "message"])


def utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
