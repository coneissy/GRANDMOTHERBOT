from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Iterator
from urllib.parse import quote as urlquote
import gzip
import io
import pandas as pd
import requests


TARDIS_DATASET_BASE = "https://datasets.tardis.dev/v1/binance/quotes"
TARDIS_API_BASE = "https://api.tardis.dev/v1"
PAPER_CEX_FEE_RATE = Decimal("0.0001725")
USDT_USD = Decimal("1")
QUOTE_COLUMNS = (
    "exchange",
    "symbol",
    "timestamp",
    "local_timestamp",
    "ask_amount",
    "ask_price",
    "bid_price",
    "bid_amount",
)


@dataclass(frozen=True)
class TardisQuote:
    symbol: str
    timestamp_us: int
    local_timestamp_us: int
    bid_price: Decimal
    ask_price: Decimal

    @property
    def mid_price(self) -> Decimal:
        return (self.bid_price + self.ask_price) / Decimal("2")


@dataclass(frozen=True)
class QuoteMatch:
    target_us: int
    quote: TardisQuote
    staleness_us: int


def daily_quotes_url(day: date, symbol: str) -> str:
    return (
        f"{TARDIS_DATASET_BASE}/{day:%Y/%m/%d}/"
        f"{urlquote(symbol.upper(), safe='')}.csv.gz"
    )


def _decimal(value: object) -> Decimal:
    if value is None or pd.isna(value):
        raise ValueError("missing numeric quote value")
    return Decimal(str(value))


def read_quotes_frame(frame: pd.DataFrame, symbol: str | None = None) -> list[TardisQuote]:
    missing = [c for c in QUOTE_COLUMNS if c not in frame.columns]
    if missing:
        raise ValueError(f"missing Tardis quote columns: {missing}")

    rows: list[TardisQuote] = []
    for row in frame.itertuples(index=False):
        data = row._asdict()
        if symbol is not None and str(data["symbol"]).upper() != symbol.upper():
            continue
        if pd.isna(data["bid_price"]) or pd.isna(data["ask_price"]):
            continue
        rows.append(
            TardisQuote(
                symbol=str(data["symbol"]).upper(),
                timestamp_us=int(data["timestamp"]),
                local_timestamp_us=int(data["local_timestamp"]),
                bid_price=_decimal(data["bid_price"]),
                ask_price=_decimal(data["ask_price"]),
            )
        )
    rows.sort(key=lambda q: q.timestamp_us)
    return rows


def load_daily_quotes(path: str | Path, symbol: str | None = None) -> list[TardisQuote]:
    path = Path(path)
    compression = "gzip" if path.suffix == ".gz" else None
    frame = pd.read_csv(path, compression=compression)
    return read_quotes_frame(frame, symbol=symbol)


def download_daily_quotes(
    day: date,
    symbol: str,
    destination: str | Path,
    *,
    timeout_s: int = 60,
) -> Path:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(daily_quotes_url(day, symbol), timeout=timeout_s)
    response.raise_for_status()
    destination.write_bytes(response.content)
    return destination


def _quote_timestamp_us(quote: TardisQuote) -> int:
    # Tardis normalized quotes use exchange timestamp when present and
    # local_timestamp only as the documented fallback.
    return quote.timestamp_us


def asof_quote(
    quotes: Iterable[TardisQuote],
    target_us: int,
    *,
    max_staleness_us: int | None = None,
) -> QuoteMatch | None:
    ordered = quotes if isinstance(quotes, list) else sorted(
        quotes, key=_quote_timestamp_us
    )
    best: TardisQuote | None = None
    for quote in ordered:
        ts = _quote_timestamp_us(quote)
        if ts > target_us:
            break
        best = quote
    if best is None:
        return None
    staleness = target_us - _quote_timestamp_us(best)
    if max_staleness_us is not None and staleness > max_staleness_us:
        return None
    return QuoteMatch(target_us=target_us, quote=best, staleness_us=staleness)


def iso_to_us(value: str | datetime) -> int:
    dt = datetime.fromisoformat(value) if isinstance(value, str) else value
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1_000_000)


def markout_targets(slot_time_us: int) -> tuple[int, ...]:
    return tuple(
        slot_time_us + int(Decimal("-1.0") * 1_000_000)
        + i * 500_000
        for i in range(23)
    )


def markout_horizons_s() -> tuple[Decimal, ...]:
    return tuple(Decimal("-1.0") + Decimal("0.5") * i for i in range(23))


def cex_taker_fee(notional_usd: Decimal, rate: Decimal = PAPER_CEX_FEE_RATE) -> Decimal:
    if notional_usd < 0:
        raise ValueError("notional cannot be negative")
    return notional_usd * rate


def quote_from_csv_bytes(payload: bytes, symbol: str | None = None) -> list[TardisQuote]:
    with gzip.GzipFile(fileobj=io.BytesIO(payload)) as gz:
        frame = pd.read_csv(gz)
    return read_quotes_frame(frame, symbol=symbol)
