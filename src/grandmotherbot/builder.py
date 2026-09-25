from __future__ import annotations
from datetime import datetime
from decimal import Decimal
ULTRA_SOUND_REFUND_CUTOFF=datetime.fromisoformat("2024-03-05T05:00:00+00:00")
def refund_rate(slot_time:datetime)->Decimal:return Decimal("1") if slot_time<ULTRA_SOUND_REFUND_CUTOFF else Decimal(".5")
def builder_profit(delta_coinbase:Decimal,original_bid:Decimal,bid_adjusted:bool,delta:Decimal,slot_time:datetime)->Decimal:
    return delta_coinbase if not bid_adjusted else delta_coinbase-original_bid+refund_rate(slot_time)*delta
def integrated_profit(builder_profit_usd:Decimal,searcher_pnl_usd:Decimal)->Decimal:return builder_profit_usd+searcher_pnl_usd
