from decimal import Decimal
from datetime import datetime,timezone
from grandmotherbot.concentration import hhi
from grandmotherbot.token_pairs import classify_pair
from grandmotherbot.builder import builder_profit

def test_hhi(): assert hhi([Decimal("50"),Decimal("50")])==Decimal(".5")
def test_pair(): assert classify_pair("ETH","USDC",{"ETH","USDC"},Decimal("1")).category=="major-major"
def test_ultra_sound_regimes():
    assert builder_profit(Decimal("10"),Decimal("8"),True,Decimal("4"),datetime(2024,1,1,tzinfo=timezone.utc))==Decimal("6")
    assert builder_profit(Decimal("10"),Decimal("8"),True,Decimal("4"),datetime(2024,4,1,tzinfo=timezone.utc))==Decimal("4")
