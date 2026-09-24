from collections import defaultdict
from decimal import Decimal
from .identification import CandidateTransaction, passes_all_heuristics
from .constants import MANUAL_EXCLUDED_ADDRESSES
from .markout import MarkoutPoint, TradeObservation, optimal_horizon
from .profitability import estimated_ev, estimated_pnl, inventory_adjustment_like
from .builder import aggregated_profit, is_subsidized_block
from .reconstruction import Swap, reconstruct_effective_trade

def identify_transactions(transactions, swaps_by_tx):
    identified=[]
    for _, row in transactions.iterrows():
        tx=CandidateTransaction(
            observed_public_mempool=bool(row["observed_public_mempool"]),
            first_swap_in_pool_direction=bool(row["first_swap_in_pool_direction"]),
            atomic_mev=bool(row["atomic_mev"]),
            liquidation=bool(row["liquidation"]),
            ofa_backrun=bool(row["ofa_backrun"]),
            known_router=bool(row["known_router"]),
            labeled_trading_bot=bool(row["labeled_trading_bot"]),
            ens_named_eoa_controller=bool(row["ens_named_eoa_controller"]),
            erc721_transfer=bool(row["erc721_transfer"]),
            final_pair_major_cex_listed=bool(row["final_pair_major_cex_listed"]),
            from_address=str(row["from_address"]),
        )
        if passes_all_heuristics(tx):
            identified.append(row)
    return identified

def reconstruct_rows(swaps):
    grouped=defaultdict(list)
    for _, row in swaps.iterrows():
        grouped[row["tx_hash"]].append(
            Swap(str(row["token_in"]),str(row["token_out"]),
                 Decimal(str(row["amount_in"])),Decimal(str(row["amount_out"])),
                 int(row["log_index"]))
        )
    out={}
    for tx_hash, rows in grouped.items():
        out[tx_hash]=reconstruct_effective_trade(tuple(rows))
    return out

def searcher_horizon(observations_by_searcher):
    return {s: optimal_horizon(v) for s,v in observations_by_searcher.items()}

def build_markout_observation(rows):
    first=rows.iloc[0]
    points=tuple(MarkoutPoint(Decimal(str(r.horizon_s)),
                              Decimal(str(r.token_a_usdt_mid)),
                              Decimal(str(r.token_b_usdt_mid))) for _,r in rows.sort_values("horizon_s").iterrows())
    return TradeObservation(
        amount_a=Decimal(str(first.amount_a)),
        amount_b=Decimal(str(first.amount_b)),
        dex_volume_usd=Decimal(str(first.dex_volume_usd)),
        cex_taker_fees_usd=Decimal(str(first.cex_taker_fees_usd)),
        markouts=points,
    )

def profitable_trade_statistics(markout_revenues, base_fees_usd, builder_tips_usd):
    inventory=inventory_adjustment_like(markout_revenues, base_fees_usd)
    if inventory:
        return {"inventory_adjustment":True, "ev_usd":None, "pnl_usd":None, "profit_margin":None}
    ev=estimated_ev(max(markout_revenues), base_fees_usd)
    pnl=estimated_pnl(ev,builder_tips_usd)
    return {"inventory_adjustment":False,"ev_usd":ev,"pnl_usd":pnl,"profit_margin":(pnl/ev if ev>0 else None)}

def corrected_block_profit(builder_profit, searcher_pnl):
    return aggregated_profit(builder_profit, searcher_pnl)

def subsidy_flag(builder_profit, searcher_pnl):
    return is_subsidized_block(builder_profit, builder_profit+searcher_pnl)
