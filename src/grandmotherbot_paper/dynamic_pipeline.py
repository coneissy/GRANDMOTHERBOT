from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pandas as pd

from .cex_mapping import BinanceToken, build_contract_index, map_effective_pair
from .identification import CandidateTransaction, passes_all_heuristics
from .reconstruction import Swap, reconstruct_effective_trade
from .tardis import PAPER_CEX_FEE_RATE, TardisQuote, download_daily_quotes, load_daily_quotes
from .tardis_runner import MarkoutInput, build_markout_observation


@dataclass(frozen=True)
class DynamicPipelineConfig:
    quote_cache_dir: Path
    auto_download: bool = False
    max_staleness_us: int | None = None
    fee_rate: Decimal = PAPER_CEX_FEE_RATE
    require_complete_window: bool = True


def _bool(v: object) -> bool:
    return str(v).strip().lower() in {"1", "true", "t", "yes", "y"}


def _passes_h1_h6(row: pd.Series) -> bool:
    tx = CandidateTransaction(
        _bool(row["observed_public_mempool"]),
        _bool(row["first_swap_in_pool_direction"]),
        _bool(row["atomic_mev"]),
        _bool(row["liquidation"]),
        _bool(row["ofa_backrun"]),
        _bool(row["known_router"]),
        _bool(row["labeled_trading_bot"]),
        _bool(row["ens_named_eoa_controller"]),
        _bool(row["erc721_transfer"]),
        _bool(row["final_pair_major_cex_listed"]),
        str(row.get("from_address", "")),
    )
    return passes_all_heuristics(tx)


def filter_h1_h6(transactions: pd.DataFrame) -> pd.DataFrame:
    required = {
        "observed_public_mempool", "first_swap_in_pool_direction", "atomic_mev",
        "liquidation", "ofa_backrun", "known_router", "labeled_trading_bot",
        "ens_named_eoa_controller", "erc721_transfer", "final_pair_major_cex_listed",
    }
    missing = required - set(transactions.columns)
    if missing:
        raise ValueError("transactions missing H1-H6 fields: " + ", ".join(sorted(missing)))
    return transactions.loc[transactions.apply(_passes_h1_h6, axis=1)].copy()


def _reconstruct_one(swaps: pd.DataFrame):
    ordered = swaps.sort_values("log_index")
    return reconstruct_effective_trade(tuple(
        Swap(str(row.token_in), str(row.token_out), Decimal(str(row.amount_in)),
             Decimal(str(row.amount_out)), int(row.log_index))
        for row in ordered.itertuples()
    ))


def build_markout_inputs(
    transactions: pd.DataFrame,
    swaps: pd.DataFrame,
    binance_tokens: list[BinanceToken],
    *,
    apply_h1_h6: bool = True,
) -> pd.DataFrame:
    required_tx = {"tx_hash", "block_number", "slot_time", "searcher_label", "volume_usd"}
    required_swaps = {"tx_hash", "log_index", "token_in", "token_out", "amount_in", "amount_out"}
    missing_tx = required_tx - set(transactions.columns)
    missing_swaps = required_swaps - set(swaps.columns)
    if missing_tx:
        raise ValueError("transactions missing: " + ", ".join(sorted(missing_tx)))
    if missing_swaps:
        raise ValueError("swaps missing: " + ", ".join(sorted(missing_swaps)))

    tx_source = filter_h1_h6(transactions) if apply_h1_h6 else transactions.copy()
    index = build_contract_index(binance_tokens)
    tx_by_hash = tx_source.drop_duplicates("tx_hash").set_index("tx_hash")
    rows = []

    for tx_hash, group in swaps.groupby("tx_hash", sort=False):
        tx_hash = str(tx_hash)
        if tx_hash not in tx_by_hash.index:
            continue
        tx = tx_by_hash.loc[tx_hash]
        effective = _reconstruct_one(group)
        if effective is None:
            continue
        bought_match, sold_match = map_effective_pair(
            effective.token_bought, effective.token_sold, index
        )
        if not bought_match.matched or not sold_match.matched:
            continue
        slot = pd.to_datetime(tx.slot_time, utc=True)
        rows.append({
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
        })
    return pd.DataFrame(rows)


def _quote_path(cache_dir: Path, day: date, symbol: str) -> Path:
    return cache_dir / f"{day:%Y-%m-%d}" / f"{symbol.upper()}.csv.gz"


def load_or_download_quotes(day: date, symbol: str, config: DynamicPipelineConfig) -> list[TardisQuote]:
    path = _quote_path(config.quote_cache_dir, day, symbol)
    if not path.exists():
        if not config.auto_download:
            return []
        download_daily_quotes(day, symbol, path)
    return load_daily_quotes(path, symbol=symbol)


def build_dynamic_markouts(trade_inputs: pd.DataFrame, config: DynamicPipelineConfig) -> pd.DataFrame:
    required = {
        "tx_hash", "slot_time", "block_number", "searcher_label", "amount_bought",
        "amount_sold", "dex_volume_usd", "bought_symbol", "sold_symbol",
    }
    missing = required - set(trade_inputs.columns)
    if missing:
        raise ValueError("trade_inputs missing: " + ", ".join(sorted(missing)))

    cache: dict[tuple[date, str], list[TardisQuote]] = {}
    rows = []

    def get_quotes(slot: pd.Timestamp, symbol: str) -> list[TardisQuote]:
        result: list[TardisQuote] = []
        for day in (slot.date() + timedelta(days=-1), slot.date(), slot.date() + timedelta(days=1)):
            key = (day, symbol.upper())
            if key not in cache:
                cache[key] = load_or_download_quotes(day, symbol, config)
            result.extend(cache[key])
        return sorted(result, key=lambda q: q.timestamp_us)

    expected = {Decimal("-1.0") + Decimal("0.5") * i for i in range(23)}

    for row in trade_inputs.itertuples(index=False):
        slot = pd.to_datetime(row.slot_time, utc=True)
        symbols = (str(row.bought_symbol).upper(), str(row.sold_symbol).upper())
        observation = build_markout_observation(
            MarkoutInput(
                amount_bought=Decimal(str(row.amount_bought)),
                amount_sold=Decimal(str(row.amount_sold)),
                dex_volume_usd=Decimal(str(row.dex_volume_usd)),
                slot_time_us=int(slot.timestamp() * 1_000_000),
                bought_symbol=symbols[0],
                sold_symbol=symbols[1],
            ),
            {symbol: get_quotes(slot, symbol) for symbol in symbols},
            config.fee_rate,
            config.max_staleness_us,
        )

        if config.require_complete_window and {p.horizon_s for p in observation.markouts} != expected:
            continue

        for point in observation.markouts:
            rows.append({
                "tx_hash": str(row.tx_hash),
                "block_number": int(row.block_number),
                "slot_time": slot.isoformat(),
                "searcher_label": str(row.searcher_label),
                "horizon_s": str(point.horizon_s),
                "amount_a": str(observation.amount_a),
                "amount_b": str(observation.amount_b),
                "dex_volume_usd": str(observation.dex_volume_usd),
                "token_a_usdt_mid": str(point.token_a_usdt_mid),
                "token_b_usdt_mid": str(point.token_b_usdt_mid),
                "cex_taker_fees_usd": str(observation.cex_taker_fees_usd),
            })
    return pd.DataFrame(rows)
