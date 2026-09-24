from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


D = Decimal


class SearcherPattern(str, Enum):
    PATTERN_1 = "pattern_1"
    PATTERN_2 = "pattern_2"
    PATTERN_3 = "pattern_3"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class PoolSwap:
    pool: str
    dex: str
    token_in: str
    token_out: str
    amount_in: D
    amount_out: D
    lp_fee_paid: D = D("0")

    def __post_init__(self) -> None:
        if self.amount_in < 0 or self.amount_out < 0 or self.lp_fee_paid < 0:
            raise ValueError("swap amounts and fees must be non-negative")


@dataclass(frozen=True)
class CandidateTransaction:
    tx_hash: str
    block_number: int
    slot_time_ms: int
    searcher: str | None
    swaps: tuple[PoolSwap, ...]
    observed_in_public_mempool: bool
    first_swap_in_pool_direction: bool
    is_atomic_mev: bool
    is_liquidation: bool
    is_ofa_backrun: bool
    is_known_router: bool
    is_labeled_trading_bot: bool
    controls_ens_named_eoa: bool
    contains_erc721_transfer: bool
    final_tokens_cex_listed: bool

    @property
    def is_private(self) -> bool:
        return not self.observed_in_public_mempool


@dataclass(frozen=True)
class TokenInventory:
    token: str
    quantity: D


@dataclass(frozen=True)
class MarkoutPoint:
    horizon_s: D
    token_a_usdt_mid: D
    token_b_usdt_mid: D


@dataclass(frozen=True)
class HedgeObservation:
    token_a: str
    token_b: str
    amount_a: D
    amount_b: D
    dex_volume_usd: D
    cex_taker_fee_usd: D
    markouts: tuple[MarkoutPoint, ...]

    def __post_init__(self) -> None:
        if self.dex_volume_usd <= 0:
            raise ValueError("DEX trade volume must be positive")


@dataclass(frozen=True)
class BuilderEconomics:
    builder: str
    blocks: int
    bid_value_usd: D
    builder_profit_usd: D
    searcher_pnl_usd: D | None = None

    @property
    def builder_margin(self) -> D | None:
        if self.bid_value_usd == 0:
            return None
        return self.builder_profit_usd / self.bid_value_usd

    @property
    def aggregated_profit_usd(self) -> D:
        return self.builder_profit_usd + (self.searcher_pnl_usd or D("0"))

    @property
    def aggregated_margin(self) -> D | None:
        if self.bid_value_usd == 0:
            return None
        return self.aggregated_profit_usd / self.bid_value_usd
