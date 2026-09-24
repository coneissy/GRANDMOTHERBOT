# GRANDMOTHERBOT

A clean-room implementation of the **research methodology disclosed in arXiv:2507.13023v3**:

> Measuring CEX-DEX Extracted Value and Searcher Profitability: The Darkest of the MEV Dark Forest

This repository implements the paper's data and analysis pipeline. It is **not** a live trading bot.

## Implemented paper scope

- Ethereum CEX-DEX transaction identification with Heuristics 1-6.
- Multi-swap reconstruction of the effective trade.
- Binance-listed token address cross-check support.
- Manual address exclusions listed in Appendix F.3.
- Historical Binance/Tardis markouts.
- Markout horizons -1.0s to +10.0s at 0.5s.
- Markout Revenue (MR) and Gross Return (GR).
- Searcher-specific optimal execution horizon t*.
- Pattern-3 exclusion from revenue/PnL estimation.
- Inventory-adjustment exclusion.
- Estimated Extracted Value (EV), searcher PnL, and profit margin.
- Major / ALT liquidity grouping.
- Searcher-builder exclusivity (>50%) analysis.
- Integrated builder profit correction and subsidy classification.
- Weekly/daily landscape statistics and HHI.
- Reproduction report and figures from normalized research data.

## Data used by the paper

The authors use Dune's Ethereum dex.trades data, Tardis Binance historical quotes, Binance-listed ERC-20 addresses from Etherscan/CoinMarketCap, MEV-Boost payload/bid data from relayscan.io, and Ultra Sound bid-adjustment data. See Appendix A of the paper.

Primary links:
- Paper: https://arxiv.org/html/2507.13023v3
- Dune CEX-DEX query: https://dune.com/queries/4931834
- Dune CEX-DEX dashboard: https://dune.com/rig_ef/cex-dex-dash
- Dune bot labels: https://dune.com/queries/3375615
- Dune atomic MEV query: https://dune.com/queries/3493305
- Flashbots sandwich dashboard: https://dune.com/hildobby/sandwiches
- Tardis Binance historical data: https://docs.tardis.dev/historical-data-details/binance
- Relayscan: https://www.relayscan.io/builder-profit
- Ultra Sound bid adjustment: https://github.com/ultrasoundmoney/docs/blob/main/bid_adjustment.md

## Reproduction

Put normalized data files into `data/input/` using the schemas in `data/README.md`, then:

```bash
python -m pip install -e .[dev]
pytest
python -m grandmotherbot_paper.cli validate
python -m grandmotherbot_paper.cli analyze --input data/input --output output
```

No API credentials or private keys are stored in this repository.
