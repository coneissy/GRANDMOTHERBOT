# GRANDMOTHERBOT

Research-faithful CEX-DEX arbitrage engine based on the methodology described in:

**Measuring CEX-DEX Extracted Value and Searcher Profitability: The Darkest of the MEV Dark Forest**

Scope is intentionally limited to Ethereum CEX↔DEX arbitrage. No funding, triangular, cross-CEX-only, or scalping strategy is included.

## Current implementation

- six transaction-identification heuristics
- multi-swap effective-pair reconstruction
- Binance USDT mid-price markout model
- -1.0s to +10.0s horizons at 0.5s increments
- Pattern 1 / Pattern 2 / Pattern 3 classification
- searcher-specific optimal horizon t*
- EV, PnL, and profit-margin accounting
- liquidity and trade-size observations
- builder/searcher and subsidy accounting primitives
- paper-mode execution boundary
- actual-vs-estimated PnL data model
- deterministic unit tests

Live execution is disabled by default. The repository does not contain secrets.
