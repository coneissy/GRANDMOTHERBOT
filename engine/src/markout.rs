use rust_decimal::Decimal;
use serde::{Deserialize, Serialize};
use thiserror::Error;

pub fn horizons() -> Vec<Decimal> {
    (0..23).map(|i| Decimal::new(-10 + 5 * i as i64, 1)).collect()
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct MarkoutPoint {
    pub horizon_s: Decimal,
    pub token_a_usdt_mid: Decimal,
    pub token_b_usdt_mid: Decimal,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TradeObservation {
    pub amount_a: Decimal,
    pub amount_b: Decimal,
    pub dex_volume_usd: Decimal,
    pub cex_taker_fees_usd: Decimal,
    pub base_fees_usd: Decimal,
    pub markouts: Vec<MarkoutPoint>,
}

#[derive(Debug, Error)]
pub enum MarkoutError {
    #[error("DEX volume must be positive")]
    NonPositiveVolume,
    #[error("no observations")]
    Empty,
}

pub fn markout_revenue(amount_a: Decimal, amount_b: Decimal, point: &MarkoutPoint, cex_taker_fees_usd: Decimal) -> Decimal {
    amount_a * point.token_a_usdt_mid - amount_b * point.token_b_usdt_mid - cex_taker_fees_usd
}

pub fn gross_return(observation: &TradeObservation, point: &MarkoutPoint) -> Result<Decimal, MarkoutError> {
    if observation.dex_volume_usd <= Decimal::ZERO { return Err(MarkoutError::NonPositiveVolume); }
    Ok(markout_revenue(observation.amount_a, observation.amount_b, point, observation.cex_taker_fees_usd) / observation.dex_volume_usd)
}

fn median(mut values: Vec<Decimal>) -> Result<Decimal, MarkoutError> {
    if values.is_empty() { return Err(MarkoutError::Empty); }
    values.sort();
    let n = values.len();
    if n % 2 == 1 { Ok(values[n / 2]) } else { Ok((values[n / 2 - 1] + values[n / 2]) / Decimal::from(2)) }
}

pub fn median_gr_curve(observations: &[TradeObservation]) -> Result<Vec<(Decimal, Decimal)>, MarkoutError> {
    if observations.is_empty() { return Err(MarkoutError::Empty); }
    let mut out = Vec::new();
    for horizon in horizons() {
        let values: Vec<Decimal> = observations.iter().filter_map(|o| o.markouts.iter().find(|p| p.horizon_s == horizon).map(|p| gross_return(o, p).ok())).flatten().collect();
        if !values.is_empty() { out.push((horizon, median(values)?)); }
    }
    Ok(out)
}

pub fn optimal_horizon(observations: &[TradeObservation]) -> Result<Option<Decimal>, MarkoutError> {
    let curve = median_gr_curve(observations)?;
    if curve.len() != horizons().len() { return Ok(None); }
    let mut best: Option<(Decimal, Decimal)> = None;
    for (horizon, value) in curve {
        match best {
            None => best = Some((horizon, value)),
            Some((best_h, best_v)) if value > best_v || (value == best_v && horizon > best_h) => best = Some((horizon, value)),
            _ => {}
        }
    }
    Ok(best.map(|(h, _)| h))
}

pub fn inventory_adjustment_like(observation: &TradeObservation) -> bool {
    let expected = horizons();
    if !expected.iter().all(|h| observation.markouts.iter().any(|p| p.horizon_s == *h)) { return false; }
    expected.iter().all(|h| observation.markouts.iter().find(|p| p.horizon_s == *h).map(|p| markout_revenue(observation.amount_a, observation.amount_b, p, observation.cex_taker_fees_usd) < observation.base_fees_usd).unwrap_or(false))
}

#[cfg(test)]
mod tests {
    use super::*;
    fn obs() -> TradeObservation {
        TradeObservation { amount_a: Decimal::ONE, amount_b: Decimal::ONE, dex_volume_usd: Decimal::new(100,0), cex_taker_fees_usd: Decimal::ZERO, base_fees_usd: Decimal::new(1,0), markouts: horizons().into_iter().map(|h| MarkoutPoint { horizon_s:h, token_a_usdt_mid:Decimal::new(101,0), token_b_usdt_mid:Decimal::new(100,0) }).collect() }
    }
    #[test] fn horizon_grid_is_exact() { let hs=horizons(); assert_eq!(hs.len(),23); assert_eq!(hs.first().unwrap().to_string(),"-1.0"); assert_eq!(hs.last().unwrap().to_string(),"10.0"); }
    #[test] fn optimal_horizon_uses_latest_tie() { assert_eq!(optimal_horizon(&[obs()]).unwrap(),Some(Decimal::new(100,1))); }
    #[test] fn inventory_adjustment_detected() { let mut o=obs(); for p in &mut o.markouts { p.token_a_usdt_mid=Decimal::new(99,0); } assert!(inventory_adjustment_like(&o)); }
}
