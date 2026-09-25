from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any

class TruthLevel(str, Enum):
    OBSERVED="observed"; RECONSTRUCTED="reconstructed"; ESTIMATED="estimated"; COUNTERFACTUAL="counterfactual"
class Venue(str, Enum):
    DEX="dex"; CEX="cex"
@dataclass(frozen=True)
class Evidence:
    source:str; method:str; observed_at:str|None=None; confidence:Decimal=Decimal("1"); version:str="1"; reference:str|None=None
@dataclass(frozen=True)
class ExecutionQuote:
    venue:Venue; symbol:str; side:str; quantity:Decimal; executable_price:Decimal; gross_notional_usd:Decimal
    fee_usd:Decimal=Decimal("0"); gas_usd:Decimal=Decimal("0"); price_impact_usd:Decimal=Decimal("0"); available_quantity:Decimal|None=None
    partial_fill:bool=False; execution_probability:Decimal=Decimal("1"); truth_level:TruthLevel=TruthLevel.ESTIMATED; evidence:tuple[Evidence,...]=()
@dataclass
class ArbitrageEvent:
    tx_hash:str; block_number:int; block_time:str; searcher_label:str|None; token_in:str; token_out:str; dex_volume_usd:Decimal; venue_direction:str
    atomicity:str="non_atomic"; classification:str="candidate_cex_dex"; evidence:list[Evidence]=field(default_factory=list); metadata:dict[str,Any]=field(default_factory=dict)
@dataclass(frozen=True)
class EconomicLedger:
    gross_edge_usd:Decimal; dex_fees_usd:Decimal=Decimal("0"); dex_gas_usd:Decimal=Decimal("0"); dex_impact_usd:Decimal=Decimal("0")
    cex_fees_usd:Decimal=Decimal("0"); cex_impact_usd:Decimal=Decimal("0"); builder_payment_usd:Decimal=Decimal("0"); inventory_cost_usd:Decimal=Decimal("0"); other_costs_usd:Decimal=Decimal("0"); execution_probability:Decimal=Decimal("1")
    @property
    def net_executable_pnl_usd(self)->Decimal:
        return self.gross_edge_usd-sum((self.dex_fees_usd,self.dex_gas_usd,self.dex_impact_usd,self.cex_fees_usd,self.cex_impact_usd,self.builder_payment_usd,self.inventory_cost_usd,self.other_costs_usd),Decimal("0"))
    @property
    def probability_weighted_pnl_usd(self)->Decimal:
        return self.net_executable_pnl_usd*self.execution_probability
