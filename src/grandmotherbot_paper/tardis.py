from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

import requests


UTC = timezone.utc
TARDIS_BASE_URL = "https://api.tardis.dev/v1"


class TardisAPIError(RuntimeError):
    """Raised when Tardis cannot satisfy a historical-data request."""


@dataclass(frozen=True)
class ChannelFilter:
    channel: str
    symbols: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {"channel": self.channel, "symbols": list(self.symbols)}


@dataclass(frozen=True)
class RawTardisEvent:
    exchange: str
    local_timestamp_us: int | None
    message: dict[str, Any] | None
    connected: bool
    request_date: str
    minute_offset: int


@dataclass(frozen=True)
class NormalizedCexEvent:
    exchange: str
    channel: str
    symbol: str
    exchange_timestamp_us: int | None
    local_timestamp_us: int
    capture_sequence: int
    event_type: str
    trade_id: str | None = None
    book_update_id: int | None = None
    first_update_id: int | None = None
    final_update_id: int | None = None
    side: str | None = None
    price: str | None = None
    amount: str | None = None
    best_bid: str | None = None
    best_bid_amount: str | None = None
    best_ask: str | None = None
    best_ask_amount: str | None = None
    bids: tuple[tuple[str, str], ...] = ()
    asks: tuple[tuple[str, str], ...] = ()
    is_snapshot: bool = False
    generated: bool = False
    raw_message: str = ""


def _require_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def datetime_to_us(value: datetime) -> int:
    value = _require_utc(value)
    return value.microsecond + int(value.timestamp()) * 1_000_000


def us_to_datetime(value: int) -> datetime:
    return datetime.fromtimestamp(value / 1_000_000, tz=UTC)


def parse_timestamp_us(value: str | datetime | int) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, datetime):
        return datetime_to_us(value)
    text = value.strip()
    if text.isdigit():
        return int(text)
    normalized = text.replace("Z", "+00:00")
    return datetime_to_us(datetime.fromisoformat(normalized))


def binance_api_symbol(symbol: str) -> str:
    return symbol.strip().lower()


def chunked(values: Sequence[str], size: int) -> Iterator[tuple[str, ...]]:
    if size <= 0:
        raise ValueError("chunk size must be positive")
    for start in range(0, len(values), size):
        yield tuple(values[start:start + size])


def build_binance_filters(
    symbols: Sequence[str],
    channels: Sequence[str],
    max_symbols_per_filter: int = 50,
) -> list[ChannelFilter]:
    symbols = tuple(symbols)
    channels = tuple(channels)
    if not symbols:
        raise ValueError("at least one Binance symbol is required")
    if not channels:
        raise ValueError("at least one Tardis channel is required")
    result: list[ChannelFilter] = []
    for channel in channels:
        for symbol_chunk in chunked(symbols, max_symbols_per_filter):
            result.append(
                ChannelFilter(
                    channel=channel,
                    symbols=tuple(
                        binance_api_symbol(symbol) for symbol in symbol_chunk
                    ),
                )
            )
    return result


def _unwrap_binance_message(message: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    stream = message.get("stream")
    data = message.get("data", message)
    if not isinstance(data, dict):
        raise TardisAPIError("Binance Tardis message data is not a JSON object")
    return data, stream


def _infer_channel(data: dict[str, Any], stream: str | None) -> tuple[str, bool]:
    if data.get("generated") and (stream or "").endswith("@depthSnapshot"):
        return "depthSnapshot", True

    event_type = data.get("e")
    if event_type == "trade":
        return "trade", False
    if event_type == "depthUpdate":
        return "depth", False
    if event_type == "bookTicker":
        return "bookTicker", False

    stream_text = stream or ""
    if stream_text.endswith("@depthSnapshot"):
        return "depthSnapshot", True
    if "@bookTicker" in stream_text:
        return "bookTicker", False
    if "@trade" in stream_text:
        return "trade", False
    if "@depth" in stream_text:
        return "depth", False
    return str(event_type or "unknown"), bool(data.get("generated"))


def _decimal_text(value: Any) -> str | None:
    return None if value is None else str(value)


def normalize_binance_event(
    raw: RawTardisEvent,
    capture_sequence: int,
) -> NormalizedCexEvent | None:
    if not raw.connected or raw.message is None or raw.local_timestamp_us is None:
        return None

    data, stream = _unwrap_binance_message(raw.message)
    channel, generated = _infer_channel(data, stream)

    symbol = str(data.get("s") or "").upper()
    if not symbol:
        symbol = (stream or "").split("@", 1)[0].upper()
    if not symbol:
        raise TardisAPIError("Binance event has no symbol")

    event_type = str(data.get("e") or channel)
    exchange_timestamp_us: int | None = None
    trade_id: str | None = None
    book_update_id: int | None = None
    first_update_id: int | None = None
    final_update_id: int | None = None
    side: str | None = None
    price: str | None = None
    amount: str | None = None
    best_bid: str | None = None
    best_bid_amount: str | None = None
    best_ask: str | None = None
    best_ask_amount: str | None = None
    bids: tuple[tuple[str, str], ...] = ()
    asks: tuple[tuple[str, str], ...] = ()
    is_snapshot = False

    if channel == "trade":
        if data.get("T") is not None:
            exchange_timestamp_us = int(data["T"]) * 1_000
        trade_id = str(data["t"]) if data.get("t") is not None else None
        price = _decimal_text(data.get("p"))
        amount = _decimal_text(data.get("q"))
        if data.get("m") is not None:
            side = "sell" if bool(data["m"]) else "buy"

    elif channel == "bookTicker":
        best_bid = _decimal_text(data.get("b"))
        best_bid_amount = _decimal_text(data.get("B"))
        best_ask = _decimal_text(data.get("a"))
        best_ask_amount = _decimal_text(data.get("A"))
        if data.get("u") is not None:
            book_update_id = int(data["u"])

    elif channel == "depth":
        if data.get("E") is not None:
            exchange_timestamp_us = int(data["E"]) * 1_000
        first_update_id = int(data["U"]) if data.get("U") is not None else None
        final_update_id = int(data["u"]) if data.get("u") is not None else None
        book_update_id = final_update_id
        bids = tuple(
            (
                _decimal_text(level[0]) or "",
                _decimal_text(level[1]) or "",
            )
            for level in data.get("b", [])
        )
        asks = tuple(
            (
                _decimal_text(level[0]) or "",
                _decimal_text(level[1]) or "",
            )
            for level in data.get("a", [])
        )

    elif channel == "depthSnapshot":
        is_snapshot = True
        if data.get("lastUpdateId") is not None:
            book_update_id = int(data["lastUpdateId"])
        bids = tuple(
            (
                _decimal_text(level[0]) or "",
                _decimal_text(level[1]) or "",
            )
            for level in data.get("bids", [])
        )
        asks = tuple(
            (
                _decimal_text(level[0]) or "",
                _decimal_text(level[1]) or "",
            )
            for level in data.get("asks", [])
        )

    return NormalizedCexEvent(
        exchange=raw.exchange,
        channel=channel,
        symbol=symbol,
        exchange_timestamp_us=exchange_timestamp_us,
        local_timestamp_us=raw.local_timestamp_us,
        capture_sequence=capture_sequence,
        event_type=event_type,
        trade_id=trade_id,
        book_update_id=book_update_id,
        first_update_id=first_update_id,
        final_update_id=final_update_id,
        side=side,
        price=price,
        amount=amount,
        best_bid=best_bid,
        best_bid_amount=best_bid_amount,
        best_ask=best_ask,
        best_ask_amount=best_ask_amount,
        bids=bids,
        asks=asks,
        is_snapshot=is_snapshot,
        generated=generated,
        raw_message=json.dumps(raw.message, separators=(",", ":"), sort_keys=True),
    )


class TardisHTTPClient:
    """Explicit HTTP client for GrandMother raw Tardis feed access."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        session: requests.Session | None = None,
        timeout_s: float = 60.0,
        max_retries: int = 5,
        backoff_s: float = 1.0,
    ) -> None:
        self.api_key = api_key or os.getenv("TARDIS_API_KEY")
        self.session = session or requests.Session()
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self.backoff_s = backoff_s

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept-Encoding": "gzip",
            "Accept": "application/x-ndjson,text/plain,*/*",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _get(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> requests.Response:
        for attempt in range(self.max_retries + 1):
            response = self.session.get(
                url,
                params=params,
                headers=self._headers(),
                timeout=self.timeout_s,
            )
            if response.status_code < 400:
                return response

            retryable = response.status_code == 429 or response.status_code >= 500
            if not retryable or attempt >= self.max_retries:
                detail = response.text[:500].strip()
                raise TardisAPIError(
                    f"Tardis HTTP {response.status_code}: "
                    f"{detail or 'request failed'}"
                )

            retry_after = response.headers.get("Retry-After")
            delay = (
                float(retry_after)
                if retry_after
                else self.backoff_s * (2**attempt)
            )
            time.sleep(min(delay, 30.0))

        raise AssertionError("unreachable")

    def get_api_key_info(self) -> dict[str, Any]:
        payload = self._get(f"{TARDIS_BASE_URL}/api-key-info").json()
        if not isinstance(payload, dict):
            raise TardisAPIError("unexpected /api-key-info response")
        return payload

    def get_exchange_details(self, exchange: str = "binance") -> dict[str, Any]:
        payload = self._get(f"{TARDIS_BASE_URL}/exchanges/{exchange}").json()
        if not isinstance(payload, dict):
            raise TardisAPIError("unexpected exchange-details response")
        return payload

    def get_instrument(
        self,
        symbol: str,
        exchange: str = "binance",
    ) -> dict[str, Any]:
        payload = self._get(
            f"{TARDIS_BASE_URL}/instruments/"
            f"{exchange}/{binance_api_symbol(symbol)}"
        ).json()
        if not isinstance(payload, dict):
            raise TardisAPIError("unexpected instrument response")
        return payload

    def iter_minute(
        self,
        *,
        request_date: date | str,
        minute_offset: int,
        filters: Sequence[ChannelFilter],
        exchange: str = "binance",
    ) -> Iterator[RawTardisEvent]:
        if isinstance(request_date, str):
            request_date = date.fromisoformat(request_date[:10])
        if not 0 <= minute_offset <= 1439:
            raise ValueError("minute_offset must be between 0 and 1439")

        query = {
            "from": request_date.isoformat(),
            "offset": minute_offset,
            "filters": json.dumps(
                [item.as_dict() for item in filters],
                separators=(",", ":"),
            ),
        }
        response = self._get(
            f"{TARDIS_BASE_URL}/data-feeds/{exchange}",
            params=query,
        )

        for raw_line in response.text.splitlines():
            if not raw_line.strip():
                yield RawTardisEvent(
                    exchange=exchange,
                    local_timestamp_us=None,
                    message=None,
                    connected=False,
                    request_date=request_date.isoformat(),
                    minute_offset=minute_offset,
                )
                continue

            timestamp_text, separator, message_text = raw_line.partition(" ")
            if not separator:
                raise TardisAPIError("malformed Tardis NDJSON line")
            local_timestamp_us = parse_timestamp_us(timestamp_text)
            try:
                message = json.loads(message_text)
            except json.JSONDecodeError as exc:
                raise TardisAPIError(
                    "malformed JSON in Tardis data feed"
                ) from exc
            if not isinstance(message, dict):
                raise TardisAPIError(
                    "Tardis Binance message is not a JSON object"
                )

            yield RawTardisEvent(
                exchange=exchange,
                local_timestamp_us=local_timestamp_us,
                message=message,
                connected=True,
                request_date=request_date.isoformat(),
                minute_offset=minute_offset,
            )

    def iter_window(
        self,
        *,
        start: datetime,
        end: datetime,
        symbols: Sequence[str],
        channels: Sequence[str],
        exchange: str = "binance",
    ) -> Iterator[RawTardisEvent]:
        start = _require_utc(start)
        end = _require_utc(end)
        if end <= start:
            raise ValueError("window end must be after window start")

        filters = build_binance_filters(symbols, channels)
        start_us = datetime_to_us(start)
        end_us = datetime_to_us(end)

        minute = start.replace(second=0, microsecond=0)
        final_minute = (
            end - timedelta(microseconds=1)
        ).replace(second=0, microsecond=0)

        while minute <= final_minute:
            day_start = minute.replace(
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
            offset = int((minute - day_start).total_seconds() // 60)

            for event in self.iter_minute(
                request_date=day_start.date(),
                minute_offset=offset,
                filters=filters,
                exchange=exchange,
            ):
                if event.local_timestamp_us is None:
                    yield event
                    continue
                if start_us <= event.local_timestamp_us < end_us:
                    yield event

            minute += timedelta(minutes=1)

    def normalized_window(
        self,
        *,
        start: datetime,
        end: datetime,
        symbols: Sequence[str],
        channels: Sequence[str],
        exchange: str = "binance",
    ) -> list[NormalizedCexEvent]:
        events: list[NormalizedCexEvent] = []
        sequence = 0
        for raw in self.iter_window(
            start=start,
            end=end,
            symbols=symbols,
            channels=channels,
            exchange=exchange,
        ):
            normalized = normalize_binance_event(raw, sequence)
            if normalized is not None:
                events.append(normalized)
                sequence += 1

        events.sort(
            key=lambda item: (
                item.local_timestamp_us,
                item.capture_sequence,
            )
        )
        return events

    def python_replay(
        self,
        *,
        from_date: str | datetime,
        to_date: str | datetime,
        symbols: Sequence[str],
        channels: Sequence[str],
    ) -> Any:
        """Replay through the maintained tardis-dev Python client."""
        try:
            from tardis_dev import Channel, replay
        except ImportError as exc:
            raise RuntimeError(
                "Install the optional Tardis client with "
                "pip install tardis-dev, or use the built-in HTTP client."
            ) from exc

        channel_filters = [
            Channel(
                name=channel,
                symbols=[
                    binance_api_symbol(symbol)
                    for symbol in symbols
                ],
            )
            for channel in channels
        ]

        async def _replay() -> Any:
            sequence = 0
            async for local_timestamp, message in replay(
                exchange="binance",
                from_date=from_date,
                to_date=to_date,
                filters=channel_filters,
                api_key=self.api_key,
            ):
                raw = RawTardisEvent(
                    exchange="binance",
                    local_timestamp_us=datetime_to_us(local_timestamp),
                    message=message,
                    connected=True,
                    request_date=str(from_date)[:10],
                    minute_offset=0,
                )
                event = normalize_binance_event(raw, sequence)
                if event is not None:
                    sequence += 1
                    yield event

        return _replay()

    def download_datasets(
        self,
        *,
        from_date: str,
        to_date: str,
        symbols: Sequence[str],
        data_types: Sequence[str],
        download_dir: str | Path = "data/tardis/datasets",
    ) -> Any:
        """Download Tardis normalized CSV datasets using tardis-dev."""
        try:
            from tardis_dev import datasets
        except ImportError as exc:
            raise RuntimeError(
                "Install the optional Tardis extra with `pip install -e .[tardis]`."
            ) from exc

        if not symbols:
            raise ValueError("at least one symbol is required")
        if not data_types:
            raise ValueError("at least one dataset type is required")

        return datasets.download(
            exchange="binance",
            data_types=list(data_types),
            from_date=from_date,
            to_date=to_date,
            symbols=[binance_api_symbol(symbol) for symbol in symbols],
            api_key=self.api_key,
            download_dir=str(download_dir),
        )


def write_normalized_parquet(
    events: Sequence[NormalizedCexEvent],
    path: str | Path,
) -> Path:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise RuntimeError(
            "Parquet output requires the optional parquet extra."
        ) from exc

    rows: list[dict[str, Any]] = []
    for event in events:
        rows.append(
            {
                "exchange": event.exchange,
                "channel": event.channel,
                "symbol": event.symbol,
                "exchange_timestamp_us": event.exchange_timestamp_us,
                "local_timestamp_us": event.local_timestamp_us,
                "capture_sequence": event.capture_sequence,
                "event_type": event.event_type,
                "trade_id": event.trade_id,
                "book_update_id": event.book_update_id,
                "first_update_id": event.first_update_id,
                "final_update_id": event.final_update_id,
                "side": event.side,
                "price": event.price,
                "amount": event.amount,
                "best_bid": event.best_bid,
                "best_bid_amount": event.best_bid_amount,
                "best_ask": event.best_ask,
                "best_ask_amount": event.best_ask_amount,
                "bids_json": json.dumps(event.bids, separators=(",", ":")),
                "asks_json": json.dumps(event.asks, separators=(",", ":")),
                "is_snapshot": event.is_snapshot,
                "generated": event.generated,
                "raw_message": event.raw_message,
            }
        )

    table = pa.Table.from_pylist(rows)
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, output, compression="zstd")
    return output
