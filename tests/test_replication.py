from decimal import Decimal
from datetime import datetime, timezone
from grandmotherbot_paper.constants import HORIZONS, KNOWN_PATTERN_BY_SEARCHER
from grandmotherbot_paper.identification import CandidateTransaction, passes_all_heuristics
from grandmotherbot_paper.reconstruction import Swap, reconstruct_effective_trade
from grandmotherbot_paper.markout import MarkoutPoint, TradeObservation, optimal_horizon
from grandmotherbot_paper.profitability import estimated_ev, estimated_pnl, profit_margin, inventory_adjustment_like
from grandmotherbot_paper.builder import builder_profit_usd, is_subsidized_block, is_exclusive_searcher
from grandmotherbot_paper.liquidity import pair_class

def test_exact_horizons():
    assert HORIZONS[0]==Decimal("-1.0")
    assert HORIZONS[-1]==Decimal("10.0")
    assert len(HORIZONS)==23

def test_heuristics():
    good=CandidateTransaction(False,True,False,False,False,False,False,False,False,True)
    assert passes_all_heuristics(good)
    assert not passes_all_heuristics(CandidateTransaction(True,True,False,False,False,False,False,False,False,True))

def test_manual_exclusion():
    bad=CandidateTransaction(False,True,False,False,False,False,False,False,False,True,"0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789")
    assert not passes_all_heuristics(bad)

def test_reconstruction():
    e=reconstruct_effective_trade((
        Swap("A","B",Decimal("10"),Decimal("20"),0),
        Swap("B","C",Decimal("20"),Decimal("30"),1),
    ))
    assert e.token_bought=="C" and e.amount_bought==Decimal("30")
    assert e.token_sold=="A" and e.amount_sold==Decimal("10")

def test_t_star():
    pts=tuple(MarkoutPoint(h,Decimal("100")+Decimal(i),Decimal("1")) for i,h in enumerate(HORIZONS))
    o=TradeObservation(Decimal("1"),Decimal("99"),Decimal("100"),Decimal("0"),pts)
    assert optimal_horizon([o])==Decimal("10.0")

def test_accounting():
    ev=estimated_ev(Decimal("100"),Decimal("20"))
    pnl=estimated_pnl(ev,Decimal("10"))
    assert ev==Decimal("80") and pnl==Decimal("70")
    assert profit_margin(ev,pnl)==Decimal("0.875")
    assert profit_margin(Decimal("-1"),Decimal("-11")) is None
    assert inventory_adjustment_like([Decimal("0"),Decimal("0.9")],Decimal("1"))

def test_builder_formula():
    dt=datetime(2024,1,1,tzinfo=timezone.utc)
    assert builder_profit_usd(Decimal("10"),Decimal("4"),True,Decimal("2"),dt)==Decimal("8")
    assert is_subsidized_block(Decimal("-1"),Decimal("-2"))
    assert not is_subsidized_block(Decimal("1"),Decimal("-2"))
    assert is_exclusive_searcher(Decimal("51"),Decimal("100"))
    assert not is_exclusive_searcher(Decimal("50"),Decimal("100"))

def test_liquidity_groups():
    assert pair_class("WETH","USDC")=="Major-Major"
    assert pair_class("WETH","ABC")=="Major-ALT"
    assert pair_class("ABC","XYZ")=="ALT-ALT"

def test_published_pattern_table():
    assert KNOWN_PATTERN_BY_SEARCHER["Bard"]==(None,3)
    assert KNOWN_PATTERN_BY_SEARCHER["Wintermute"]==(Decimal("1.5"),1)
