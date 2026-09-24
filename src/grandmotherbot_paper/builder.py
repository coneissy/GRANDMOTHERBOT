from decimal import Decimal

def is_exclusive_searcher(volume_to_primary_builder: Decimal, total_volume: Decimal) -> bool:
    if total_volume <= 0:
        raise ValueError("total volume must be positive")
    return volume_to_primary_builder / total_volume > Decimal("0.50")

def aggregated_profit(builder_profit_usd: Decimal, searcher_pnl_usd: Decimal) -> Decimal:
    return builder_profit_usd + searcher_pnl_usd

def is_subsidized_block(builder_profit_usd: Decimal, aggregated_profit_usd: Decimal) -> bool:
    return builder_profit_usd < 0 and aggregated_profit_usd < 0