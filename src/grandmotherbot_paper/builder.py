from datetime import datetime
from decimal import Decimal

def ultra_sound_refund_rate(slot_time: datetime) -> Decimal:
    cutoff=datetime.fromisoformat("2024-03-05T05:00:00+00:00")
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
    return delta_coinbase_usd-original_bid_value_usd+ultra_sound_refund_rate(slot_time)*bid_adjustment_delta_usd

def aggregated_profit(builder_profit_value_usd: Decimal, searcher_pnl_usd: Decimal) -> Decimal:
    return builder_profit_value_usd+searcher_pnl_usd

def aggregated_profit_margin(
    aggregated_profit_value_usd: Decimal,
    original_bid_value_usd: Decimal,
    bid_adjustment_delta_usd: Decimal,
    slot_time: datetime,
    bid_adjusted: bool,
) -> Decimal | None:
    r=ultra_sound_refund_rate(slot_time) if bid_adjusted else Decimal("0")
    denominator=aggregated_profit_value_usd+original_bid_value_usd-r*bid_adjustment_delta_usd
    return aggregated_profit_value_usd/denominator if denominator != 0 else None

def is_subsidized_block(builder_profit_value_usd: Decimal, aggregated_profit_value_usd: Decimal) -> bool:
    return builder_profit_value_usd<0 and aggregated_profit_value_usd<0

def is_exclusive_searcher(volume_to_primary_builder: Decimal, total_volume: Decimal) -> bool:
    if total_volume<=0:
        raise ValueError("total volume must be positive")
    return volume_to_primary_builder/total_volume>Decimal("0.50")
