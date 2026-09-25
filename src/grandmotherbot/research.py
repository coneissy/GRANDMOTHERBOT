from dataclasses import dataclass
@dataclass(frozen=True)
class ResearchClaim:
    claim_id:str; paper:str; section:str; claim:str; data_required:str; formula:str; assumption:str; status:str="planned"; result:str|None=None
CLAIMS=[
ResearchClaim("GM-001","2507.13023v3","A-H","Replication of candidate/exclusion funnel","DEX trades; CEX quotes","Appendix H counts","Binance universe and paper heuristics"),
ResearchClaim("GM-002","2507.13023v3","4.1","Searcher-specific optimal horizon","CEX markouts","argmax_t median(GR_j(t))","mid-price markout"),
ResearchClaim("GM-003","2507.13023v3","G","Integrated searcher-builder economics","MEV-Boost; Ultra Sound","BP=ΔC-b+rδ","dated refund regimes"),
ResearchClaim("GM-004","2507.13023v3","5.2","Executable hedge impact","CEX order books","VWAP(q,t)-mid(t)","historical depth available"),
ResearchClaim("GM-005","GrandMother","CEX-DEX","Execution-constrained PnL","DEX state; CEX depth; gas; inclusion","max_q net PnL(q)","modelled execution probabilities")]
