from datetime import datetime
from decimal import Decimal


ULTRA_SOUND_BID_ADJUSTMENT_BLOCK = 18_719_819
ULTRA_SOUND_REFUND_CUTOFF = datetime.fromisoformat("2024-03-05T05:00:00+00:00")


def ultra_sound_refund_rate(slot_time: datetime) -> Decimal:
    return Decimal("1.0") if slot_time < ULTRA_SOUND_REFUND_CUTOFF else Decimal("0.5")


def builder_profit_eth(
    delta_coinbase_eth: Decimal,
    original_bid_value_eth: Decimal,
    bid_adjusted: bool,
    bid_adjustment_delta_eth: Decimal,
    slot_time: datetime,
) -> Decimal:
    """Appendix G formula in ETH before USD conversion."""
    if not bid_adjusted:
        return delta_coinbase_eth
    return (
        delta_coinbase_eth
        - original_bid_value_eth
        + ultra_sound_refund_rate(slot_time) * bid_adjustment_delta_eth
    )


def eth_to_usd(value_eth: Decimal, eth_usdt_mid: Decimal) -> Decimal:
    if eth_usdt_mid <= 0:
        raise ValueError("ETH-USDT mid-price must be positive")
    return value_eth * eth_usdt_mid


def builder_profit_usd(
    delta_coinbase_usd: Decimal,
    original_bid_value_usd: Decimal,
    bid_adjusted: bool,
    bid_adjustment_delta_usd: Decimal,
    slot_time: datetime,
) -> Decimal:
    """Compatibility path for already-normalized USD inputs."""
    if not bid_adjusted:
        return delta_coinbase_usd
    return (
        delta_coinbase_usd
        - original_bid_value_usd
        + ultra_sound_refund_rate(slot_time) * bid_adjustment_delta_usd
    )


def builder_profit_from_eth_usd(
    delta_coinbase_eth: Decimal,
    original_bid_value_eth: Decimal,
    bid_adjusted: bool,
    bid_adjustment_delta_eth: Decimal,
    eth_usdt_mid: Decimal,
    slot_time: datetime,
) -> Decimal:
    """Exact paper path: calculate builder profit in ETH, then convert at slot-time ETH-USDT mid."""
    return eth_to_usd(
        builder_profit_eth(
            delta_coinbase_eth,
            original_bid_value_eth,
            bid_adjusted,
            bid_adjustment_delta_eth,
            slot_time,
        ),
        eth_usdt_mid,
    )


def aggregated_profit(builder_profit_value_usd: Decimal, searcher_pnl_usd: Decimal) -> Decimal:
    return builder_profit_value_usd + searcher_pnl_usd


def aggregated_profit_margin(
    aggregated_profit_value_usd: Decimal,
    original_bid_value_usd: Decimal,
    bid_adjustment_delta_usd: Decimal,
    slot_time: datetime,
    bid_adjusted: bool,
) -> Decimal | None:
    r = ultra_sound_refund_rate(slot_time) if bid_adjusted else Decimal("0")
    denominator = (
        aggregated_profit_value_usd
        + original_bid_value_usd
        - r * bid_adjustment_delta_usd
    )
    return (
        aggregated_profit_value_usd / denominator
        if denominator != 0
        else None
    )


def is_subsidized_block(
    builder_profit_value_usd: Decimal,
    aggregated_profit_value_usd: Decimal,
) -> bool:
    return builder_profit_value_usd < 0 and aggregated_profit_value_usd < 0


def is_exclusive_searcher(
    volume_to_primary_builder: Decimal,
    total_volume: Decimal,
) -> bool:
    if total_volume <= 0:
        raise ValueError("total volume must be positive")
    return volume_to_primary_builder / total_volume > Decimal("0.50")
