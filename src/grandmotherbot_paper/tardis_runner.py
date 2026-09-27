from dataclasses import dataclass
from decimal import Decimal
from typing import Callable

from .constants import HORIZONS
from .markout import MarkoutPoint, TradeObservation
from .tardis import TardisQuote, asof_quote, markout_targets


@dataclass(frozen=True)
class MarkoutInput:
    amount_bought: Decimal
    amount_sold: Decimal
    dex_volume_usd: Decimal
    slot_time_us: int
    bought_symbol: str
    sold_symbol: str
    base_fees_usd: Decimal = Decimal("0")


def two_leg_cex_fee(dex_volume_usd: Decimal, fee_rate: Decimal) -> Decimal:
    """Two CEX taker legs, using the DEX trade USD notional for each leg."""
    if dex_volume_usd <= 0:
        raise ValueError("DEX volume must be positive")
    return Decimal("2") * dex_volume_usd * fee_rate


def build_markout_observation(
    trade: MarkoutInput,
    quotes_by_symbol: dict[str, list[TardisQuote]],
    fee_rate: Decimal,
    max_staleness_us: int | None = None,
    quote_selector: Callable = asof_quote,
) -> TradeObservation:
    if trade.dex_volume_usd <= 0:
        raise ValueError("DEX volume must be positive")
    if trade.amount_bought <= 0 or trade.amount_sold <= 0:
        raise ValueError("trade amounts must be positive")
    if trade.bought_symbol == trade.sold_symbol:
        raise ValueError("bought and sold Binance symbols must differ")

    bought_quotes = quotes_by_symbol.get(trade.bought_symbol, [])
    sold_quotes = quotes_by_symbol.get(trade.sold_symbol, [])
    points: list[MarkoutPoint] = []
    fee = two_leg_cex_fee(trade.dex_volume_usd, fee_rate)

    for horizon_s, target_us in zip(HORIZONS, markout_targets(trade.slot_time_us)):
        bought = quote_selector(bought_quotes, target_us, max_staleness_us)
        sold = quote_selector(sold_quotes, target_us, max_staleness_us)
        if bought is None or sold is None:
            continue
        points.append(
            MarkoutPoint(
                horizon_s,
                bought.quote.mid_price,
                sold.quote.mid_price,
            )
        )

    return TradeObservation(
        amount_a=trade.amount_bought,
        amount_b=trade.amount_sold,
        dex_volume_usd=trade.dex_volume_usd,
        cex_taker_fees_usd=fee,
        markouts=tuple(points),
        base_fees_usd=trade.base_fees_usd,
    )
