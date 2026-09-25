from decimal import Decimal
from grandmotherbot.cex import OrderBook
from grandmotherbot.dex import ConstantProductPool
from grandmotherbot.inventory import inventory_carry_cost
def test_cex_walks_book():
    q=OrderBook([(Decimal("99"),Decimal("10"))],[(Decimal("100"),Decimal("5")),(Decimal("101"),Decimal("10"))]).execute("buy",Decimal("10"))
    assert q.quantity==Decimal("10") and q.executable_price==Decimal("100.5") and q.price_impact_usd==Decimal("5")
def test_dex_quote_has_size_dependent_impact():
    q=ConstantProductPool(Decimal("1000"),Decimal("1000"),Decimal("30")).quote(Decimal("100"))
    assert q.amount_out>0 and q.price_impact_usd>0
def test_inventory_cost(): assert inventory_carry_cost(Decimal("100000"),Decimal("3600"),Decimal(".05"))>0
