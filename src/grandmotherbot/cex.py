from __future__ import annotations
from decimal import Decimal
from typing import Iterable
from .models import ExecutionQuote, Venue, TruthLevel
class OrderBook:
    def __init__(self,bids:Iterable[tuple[Decimal,Decimal]],asks:Iterable[tuple[Decimal,Decimal]]):
        self.bids=sorted(bids,key=lambda x:x[0],reverse=True); self.asks=sorted(asks,key=lambda x:x[0])
    def execute(self,side:str,quantity:Decimal,fee_bps:Decimal=Decimal("0"))->ExecutionQuote:
        if quantity<=0: raise ValueError("quantity must be positive")
        levels=self.asks if side.lower()=="buy" else self.bids; remaining=quantity; notional=Decimal("0"); filled=Decimal("0")
        for price,size in levels:
            take=min(remaining,size); notional+=take*price; filled+=take; remaining-=take
            if remaining<=0: break
        if filled<=0: raise ValueError("no executable liquidity")
        vwap=notional/filled; fee=notional*fee_bps/Decimal("10000"); best=levels[0][0]
        impact=abs(vwap-best)*filled
        return ExecutionQuote(Venue.CEX,"",side.lower(),filled,vwap,notional,fee,Decimal("0"),impact,filled,filled<quantity,Decimal("1") if filled==quantity else filled/quantity,TruthLevel.ESTIMATED)

def best_executable_quote(books:dict[str,OrderBook],side:str,quantity:Decimal,fee_bps:dict[str,Decimal]|None=None):
    fee_bps=fee_bps or {}; quotes=[]
    for venue,book in books.items(): quotes.append((venue,book.execute(side,quantity,fee_bps.get(venue,Decimal("0")))))
    return min(quotes,key=lambda x:x[1].fee_usd+x[1].price_impact_usd) if quotes else None
