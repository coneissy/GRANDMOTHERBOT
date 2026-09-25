from decimal import Decimal
from .models import ExecutionQuote,EconomicLedger
def ledger_from_quotes(dex:ExecutionQuote,cex:ExecutionQuote,builder_payment_usd:Decimal=Decimal("0"),inventory_cost_usd:Decimal=Decimal("0"))->EconomicLedger:
    gross=dex.gross_notional_usd-cex.gross_notional_usd
    return EconomicLedger(gross,dex.fee_usd,dex.gas_usd,dex.price_impact_usd,cex.fee_usd,cex.price_impact_usd,builder_payment_usd,inventory_cost_usd,Decimal("0"),min(dex.execution_probability,cex.execution_probability))
def paper_vs_executable(paper_pnl_usd:Decimal,executable:EconomicLedger)->dict[str,Decimal]:
    return {"paper_pnl_usd":paper_pnl_usd,"executable_pnl_usd":executable.net_executable_pnl_usd,"difference_usd":executable.net_executable_pnl_usd-paper_pnl_usd}
