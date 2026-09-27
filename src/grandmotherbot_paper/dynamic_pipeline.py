from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd

from .cex_mapping import BinanceToken, build_contract_index, map_effective_pair
from .reconstruction import Swap, reconstruct_effective_trade
from .tardis import PAPER_CEX_FEE_RATE, TardisQuote, download_daily_quotes, load_daily_quotes
from .tardis_runner import MarkoutInput, build_markout_observation


@dataclass(frozen=True)
class DynamicPipelineConfig:
    quote_cache_dir: Path
    auto_download: bool = False
    max_staleness_us: int | None = None
    fee_rate: Decimal = PAPER_CEX_FEE_RATE


def _reconstruct_one(swaps: pd.DataFrame):
    ordered = swaps.sort_values("log_index")
    return reconstruct_effective_trade(
        tuple(
            Swap(
                str(row.token_in),
                str(row.token_out),
                Decimal(str(row.amount_in)),
                Decimal(str(row.amount_out)),
                int(row.log_index),
            )
            for row in ordered.itertuples()
        )
    )


def build_markout_inputs(
    transactions: pd.DataFrame,
    swaps: pd.DataFrame,
    binance_tokens: list[BinanceToken],
) -> pd.DataFrame:
    required_tx = {
        "tx_hash", "block_number", "slot_time", "searcher_label", "volume_usd",
    }
    required_swaps = {
        "tx_hash", "log_index", "token_in", "token_out", "amount_in", "amount_out",
    }
    missing_tx = required_tx - set(transactions.columns)
    missing_swaps = required_swaps - set(swaps.columns)
    if missing_tx:
        raise ValueError("transactions missing: " + ", ".join(sorted(missing_tx)))
    if missing_swaps:
        raise ValueError("swaps missing: " + ", ".join(sorted(missing_swaps)))

    index = build_contract_index(binance_tokens)
    tx_by_hash = transactions.drop_duplicates("tx_hash").set_index("tx_hash")
    rows = []

    for tx_hash, group in swaps.groupby("tx_hash", sort=False):
        tx_hash = str(tx_hash)
        if tx_hash not in tx_by_hash.index:
            continue
        tx = tx_by_hash.loc[tx_hash]
        effective = _reconstruct_one(group)
        bought = map_effective_pair(effective.token_bought, effective.token_sold, index)
        bought_match, sold_match = bought
        if not bought_match.matched or not sold_match.matched:
            continue
        slot = pd.to_datetime(tx.slot_time, utc=True)
        rows.append(
            {
                "tx_hash": tx_hash,
                "block_number": int(tx.block_number),
                "slot_time": slot,
                "searcher_label": str(tx.searcher_label),
                "amount_bought": str(effective.amount_bought),
                "amount_sold": str(effective.amount_sold),
                "dex_volume_usd": str(tx.volume_usd),
                "bought_contract": bought_match.contract_address,
                "sold_contract": sold_match.contract_address,
                "bought_symbol": bought_match.symbol,
                "sold_symbol": sold_match.symbol,
            }
        )

    return pd.DataFrame(rows)


def _quote_path(cache_dir: Path, day: date, symbol: str) -> Path:
    return cache_dir / f"{day:%Y-%m-%d}" / f"{symbol.upper()}.csv.gz"


def load_or_download_quotes(
    day: date,
    symbol: str,
    config: DynamicPipelineConfig,
) -> list[TardisQuote]:
    path = _quote_path(config.quote_cache_dir, day, symbol)
    if not path.exists():
        if not config.auto_download:
            return []
        download_daily_quotes(day, symbol, path)
    return load_daily_quotes(path, symbol=symbol)


def build_dynamic_markouts(
    trade_inputs: pd.DataFrame,
    config: DynamicPipelineConfig,
) -> pd.DataFrame:
    required = {
        "tx_hash", "slot_time", "searcher_label", "amount_bought",
        "amount_sold", "dex_volume_usd", "bought_symbol", "sold_symbol",
    }
    missing = required - set(trade_inputs.columns)
    if missing:
        raise ValueError("trade_inputs missing: " + ", ".join(sorted(missing)))

    cache: dict[tuple[date, str], list[TardisQuote]] = {}
    rows = []

    for row in trade_inputs.itertuples(index=False):
        slot = pd.to_datetime(row.slot_time, utc=True)
        day = slot.date()
        slot_us = int(slot.timestamp() * 1_000_000)
        symbols = (str(row.bought_symbol).upper(), str(row.sold_symbol).upper())
        quotes = {}
        for symbol in symbols:
            key = (day, symbol)
            if key not in cache:
                cache[key] = load_or_download_quotes(day, symbol, config)
            quotes[symbol] = cache[key]

        observation = build_markout_observation(
            MarkoutInput(
                amount_bought=Decimal(str(row.amount_bought)),
                amount_sold=Decimal(str(row.amount_sold)),
                dex_volume_usd=Decimal(str(row.dex_volume_usd)),
                slot_time_us=slot_us,
                bought_symbol=symbols[0],
                sold_symbol=symbols[1],
            ),
            quotes,
            config.fee_rate,
            config.max_staleness_us,
        )

        for point in observation.markouts:
            rows.append(
                {
                    "tx_hash": str(row.tx_hash),
                    "block_number": int(row.block_number),
                    "slot_time": slot.isoformat(),
                    "searcher_label": str(row.searcher_label),
                    "horizon_s": str(point.horizon_s),
                    "amount_a": str(observation.amount_a),
                    "amount_b": str(observation.amount_b),
                    "token_a_usdt_mid": str(point.token_a_usdt_mid),
                    "token_b_usdt_mid": str(point.token_b_usdt_mid),
                    "cex_taker_fees_usd": str(observation.cex_taker_fees_usd),
                    "dex_volume_usd": str(observation.dex_volume_usd),
                }
            )

    return pd.DataFrame(rows)
