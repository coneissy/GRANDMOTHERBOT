# GRANDMOTHERBOT

GRANDMOTHERBOT is a research-faithful implementation of the methodology in:

> Fei Wu, Danning Sui, Thomas Thiery, Mallesh Pai et al., "Measuring CEX-DEX Extracted Value and Searcher Profitability: The Darkest of the MEV Dark Forest", arXiv:2507.13023v3.

The live strategy scope is intentionally restricted to **Ethereum CEX↔DEX arbitrage**.

It implements the paper's core observable methodology:

- six CEX-DEX identification heuristics
- sequential multi-swap reconstruction
- Binance USDT mid-price valuation
- -1.0s through +10.0s markout horizons in 0.5s increments
- MR and GR calculations
- searcher-specific optimal execution horizon t*
- Pattern 1 / Pattern 2 / Pattern 3 classification
- EV, builder-tip, PnL, and profit-margin accounting
- liquidity-aware size evaluation
- builder/searcher integration analytics
- the paper's subsidized-block definition
- estimated-versus-realized PnL storage

The execution boundary is DEX-first, then CEX hedge after on-chain confirmation.

**Live execution is disabled by default. No credentials belong in source control.**

## Run

```bash
python -m pytest
python -m grandmother.cli --demo
```

## Research references

- Paper: https://arxiv.org/html/2507.13023v3
- Dune CEX-DEX query: https://dune.com/queries/4931834
- Dune bot labels: https://dune.com/queries/3375615
- Dune Ethereum DEX trades: https://docs.dune.com/data-catalog/evm/ethereum/curated-data/dex/dex-trades
- Tardis Binance data: https://docs.tardis.dev/historical-data-details/binance
- MEV-Boost: https://docs.flashbots.net/flashbots-mev-boost/
- Ultra Sound bid adjustment: https://github.com/ultrasoundmoney/docs/blob/main/bid_adjustment.md
