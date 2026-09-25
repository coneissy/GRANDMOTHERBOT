use rust_decimal::Decimal;
use serde::{Deserialize, Serialize};
use thiserror::Error;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DexQuote { pub amount_in: Decimal, pub amount_out: Decimal, pub fee_usd: Decimal, pub gas_usd: Decimal }
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CexLevel { pub price: Decimal, pub quantity: Decimal }
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CexDepth { pub bids: Vec<CexLevel>, pub asks: Vec<CexLevel>, pub taker_fee_rate: Decimal }
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CostModel { pub builder_tip_usd: Decimal, pub additional_slippage_usd: Decimal, pub hedge_failure_cost_usd: Decimal }
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionRisk { pub inclusion_probability: Decimal, pub hedge_fill_probability: Decimal }
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SimulationInput { pub token_a_amount: Decimal, pub token_b_amount: Decimal, pub dex_quote: DexQuote, pub cex: CexDepth, pub costs: CostModel, pub risk: ExecutionRisk }
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionSimulation { pub hedge_proceeds_usd: Decimal, pub hedge_cost_usd: Decimal, pub cex_fees_usd: Decimal, pub gas_usd: Decimal, pub builder_tip_usd: Decimal, pub slippage_usd: Decimal, pub net_if_fully_hedged_usd: Decimal, pub expected_pnl_usd: Decimal, pub expected_edge_bps: Decimal }
#[derive(Debug, Error)]
pub enum SimulationError { #[error("amount must be positive")] NonPositiveAmount, #[error("insufficient CEX depth")] InsufficientDepth, #[error("probabilities must be in [0,1]")] InvalidProbability, #[error("AMM reserves and amount must be positive")] InvalidAmm, #[error("CEX bid/ask book is empty")] EmptyBook }

pub fn simulate_constant_product_exact_in(reserve_in: Decimal, reserve_out: Decimal, amount_in: Decimal, fee_bps: Decimal) -> Result<Decimal, SimulationError> {
    if reserve_in <= Decimal::ZERO || reserve_out <= Decimal::ZERO || amount_in <= Decimal::ZERO { return Err(SimulationError::InvalidAmm); }
    let fee_factor=Decimal::ONE-fee_bps/Decimal::new(10_000,0); if fee_factor<=Decimal::ZERO { return Err(SimulationError::InvalidAmm); }
    let effective_in=amount_in*fee_factor; Ok(reserve_out*effective_in/(reserve_in+effective_in))
}

fn consume_book(levels:&[CexLevel], quantity:Decimal)->Result<Decimal,SimulationError>{
    if quantity<=Decimal::ZERO{return Err(SimulationError::NonPositiveAmount);} let mut remaining=quantity; let mut notional=Decimal::ZERO;
    for level in levels { if level.price<=Decimal::ZERO||level.quantity<=Decimal::ZERO{continue;} let take=remaining.min(level.quantity); notional+=take*level.price; remaining-=take; if remaining<=Decimal::ZERO{return Ok(notional);} }
    Err(SimulationError::InsufficientDepth)
}

// Live GrandMother uses executable CEX depth, not the paper mid-price estimate.
// It sells acquired token A at bids and repurchases sold token B at asks.
pub fn simulate_execution(input:&SimulationInput)->Result<ExecutionSimulation,SimulationError>{
    if input.token_a_amount<=Decimal::ZERO||input.token_b_amount<=Decimal::ZERO{return Err(SimulationError::NonPositiveAmount);}
    if input.risk.inclusion_probability<Decimal::ZERO||input.risk.inclusion_probability>Decimal::ONE||input.risk.hedge_fill_probability<Decimal::ZERO||input.risk.hedge_fill_probability>Decimal::ONE{return Err(SimulationError::InvalidProbability);}
    if input.cex.bids.is_empty()||input.cex.asks.is_empty(){return Err(SimulationError::EmptyBook);}
    let proceeds=consume_book(&input.cex.bids,input.token_a_amount)?; let repurchase=consume_book(&input.cex.asks,input.token_b_amount)?;
    let cex_fees=(proceeds+repurchase)*input.cex.taker_fee_rate;
    let net=proceeds-repurchase-cex_fees-input.dex_quote.fee_usd-input.dex_quote.gas_usd-input.costs.builder_tip_usd-input.costs.additional_slippage_usd;
    let expected_if_included=input.risk.hedge_fill_probability*net+(Decimal::ONE-input.risk.hedge_fill_probability)*(-input.costs.hedge_failure_cost_usd);
    let expected=input.risk.inclusion_probability*expected_if_included-(Decimal::ONE-input.risk.inclusion_probability)*input.costs.hedge_failure_cost_usd;
    let deployed=(proceeds+repurchase).max(Decimal::ONE);
    Ok(ExecutionSimulation{hedge_proceeds_usd:proceeds,hedge_cost_usd:repurchase,cex_fees_usd:cex_fees,gas_usd:input.dex_quote.gas_usd,builder_tip_usd:input.costs.builder_tip_usd,slippage_usd:input.costs.additional_slippage_usd,net_if_fully_hedged_usd:net,expected_pnl_usd:expected,expected_edge_bps:expected/deployed*Decimal::new(10_000,0)})
}

#[cfg(test)]
mod tests { use super::*;
#[test] fn amm_quote_respects_fee(){let out=simulate_constant_product_exact_in(Decimal::new(1_000_000,0),Decimal::new(1_000_000,0),Decimal::new(10_000,0),Decimal::new(30,0)).unwrap();assert!(out>Decimal::new(9_800,0)&&out<Decimal::new(10_000,0));}
#[test] fn executable_hedge_walks_depth(){let input=SimulationInput{token_a_amount:Decimal::ONE,token_b_amount:Decimal::ONE,dex_quote:DexQuote{amount_in:Decimal::ONE,amount_out:Decimal::ONE,fee_usd:Decimal::new(1,0),gas_usd:Decimal::new(1,0)},cex:CexDepth{bids:vec![CexLevel{price:Decimal::new(101,0),quantity:Decimal::ONE}],asks:vec![CexLevel{price:Decimal::new(100,0),quantity:Decimal::ONE}],taker_fee_rate:Decimal::new(15,4)},costs:CostModel{builder_tip_usd:Decimal::new(1,0),additional_slippage_usd:Decimal::ZERO,hedge_failure_cost_usd:Decimal::ZERO},risk:ExecutionRisk{inclusion_probability:Decimal::ONE,hedge_fill_probability:Decimal::ONE}};assert!(simulate_execution(&input).unwrap().net_if_fully_hedged_usd>Decimal::ZERO);}
}
