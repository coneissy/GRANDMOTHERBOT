from datetime import datetime
from decimal import Decimal

def ultra_sound_refund_rate(slot_time: datetime) -> Decimal:
    cutoff = datetime.fromisoformat("2024-03-05T05:00:00+00:00")
    return Decimal("1.0") if slot_time < cutoff else Decimal("0.5")

def builder_profit_usd(
    delta_coinbase_usd: Decimal,
    original_bid_value_usd: Decimal,
    bid_adjusted: bool,
    bid_adjustment_delta_usd: Decimal,
    slot_time: datetime,
) -> Decimal:
    if not bid_adjusted:
        return delta_coinbase_usd
    r = ultra_sound_refund_rate(slot_time)
    return delta_coinbase_usd - original_bid_value_usd + r * bid_adjustment_delta_usd

def aggregated_profit(builder_profit_usd_value: Decimal, searcher_pnl_usd: Decimal) -> Decimal:
    return builder_profit_usd_value + searcher_pnl_usd

def is_subsidized_block(builder_profit_usd_value: Decimal, aggregated_profit_usd: Decimal) -> bool:
    return builder_profit_usd_value < 0 and aggregated_profit_usd < 0

def is_exclusive_searcher(volume_to_primary_builder: Decimal, total_volume: Decimal) -> bool:
    if total_volume <= 0:
        raise ValueError("total volume must be positive")
    return volume_to_primary_builder / total_volume > Decimal("0.50")
