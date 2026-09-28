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
        query = QueryBase(
            name="GrandMother CEX-DEX source query",
            query_id=self.config.query_id,
        )
        if max_age_hours is not None:
            return client.get_latest_result(
                self.config.query_id, max_age_hours=max_age_hours
            )
        return client.run_query(query)


def dune_rows(result: Any) -> list[dict[str, Any]]:
    """Extract rows from common dune-client result shapes without coercion.

    The source payload remains authoritative. Unknown columns and native values
    are retained exactly as returned by the client.
    """
    payload = result
    if hasattr(payload, "result"):
        payload = payload.result

    if isinstance(payload, dict):
        rows = payload.get("rows")
        if rows is None and isinstance(payload.get("result"), dict):
            rows = payload["result"].get("rows")
    else:
        rows = getattr(payload, "rows", None)

    if rows is None:
        raise ValueError("Dune result does not contain a rows collection")
    if not isinstance(rows, (list, tuple)):
        raise TypeError("Dune rows collection must be a list or tuple")
    return [dict(row) if isinstance(row, dict) else row for row in rows]


class TardisAdapter:
    """Historical Binance Spot raw-feed adapter.

    Tardis documents this endpoint as minute-by-minute NDJSON. Each non-empty
    line contains a local/capture timestamp followed by the exchange-native
    JSON message. Raw exchange-native messages are preserved.
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
        filters = [
            {
                "channel": channel,
                **({"symbols": list(symbols)} if symbols else {}),
            }
            for channel in channels
        ]
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

        events: list[dict[str, Any]] = []
        for raw_line in payload.splitlines(keepends=False):
            if not raw_line.strip():
                # Tardis uses empty NDJSON lines as disconnect markers.
                events.append({"disconnect": True})
                continue
            local_ts, raw = raw_line.split(maxsplit=1)
            events.append(
                {
                    "capture_time": local_ts,
                    "message": json.loads(raw),
                }
            )
        return events


def parse_tardis_events(events: list[dict[str, Any]]) -> pd.DataFrame:
    """Flatten the transport envelope while preserving native event fields."""
    rows: list[dict[str, Any]] = []
    for event in events:
        if event.get("disconnect"):
            rows.append(
                {
                    "capture_time": None,
                    "message": None,
                    "disconnect": True,
                }
            )
        else:
            rows.append(
                {
                    "capture_time": event["capture_time"],
                    "message": event["message"],
                    "disconnect": False,
                }
            )
    return pd.DataFrame(
        rows,
        columns=["capture_time", "message", "disconnect"],
    )


def normalize_binance_book_ticker(events: list[dict[str, Any]]) -> pd.DataFrame:
    """Normalize Binance Spot bookTicker messages after raw capture.

    Binance-native fields are mapped, not recomputed:
    s=symbol, E=exchange event time, b/B=bid price/qty, a/A=ask price/qty.
    Tardis capture_time is retained separately for provenance.
    """
    rows: list[dict[str, Any]] = []
    for event in events:
        if event.get("disconnect"):
            continue
        message = event["message"]
        if message.get("e") not in (None, "bookTicker"):
            continue
        rows.append(
            {
                "capture_time": event["capture_time"],
                "event_time_ms": message.get("E"),
                "symbol": message.get("s"),
                "bid_price": message.get("b"),
                "bid_qty": message.get("B"),
                "ask_price": message.get("a"),
                "ask_qty": message.get("A"),
                "update_id": message.get("u"),
                "source": "tardis",
                "exchange": "binance",
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "capture_time",
            "event_time_ms",
            "symbol",
            "bid_price",
            "bid_qty",
            "ask_price",
            "ask_qty",
            "update_id",
            "source",
            "exchange",
        ],
    )


def utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
