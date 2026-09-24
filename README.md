# GRANDMOTHERBOT

Clean-room replication of the published research methodology in arXiv:2507.13023v3:
Measuring CEX-DEX Extracted Value and Searcher Profitability: The Darkest of the MEV Dark Forest.

This repository contains only the research methodology disclosed by the paper. It is not a live trading bot.

Included:
1. CEX-DEX transaction identification with Heuristics 1-6.
2. Multi-swap reconstruction of the effective token pair and aggregate amounts.
3. Binance USDT mid-price markouts from -1.0 seconds to +10.0 seconds in 0.5-second steps.
4. Markout Revenue (MR) and Gross Return (GR).
5. Searcher-specific optimal execution horizon t*.
6. Inventory-adjustment-like exclusion and Pattern 3 exclusion as described by the paper.
7. Estimated Extracted Value, searcher PnL, and profit margin.
8. Major-versus-ALT liquidity grouping metrics.
9. Exclusive-versus-neutral searcher-builder classification.
10. Integrated builder profit correction and the paper's subsidized-block rule.

Not included because they are not supplied by the paper as part of its methodology:
live wallet execution, smart-contract execution, Binance order submission, a new trading strategy, risk parameters, or unrelated arbitrage engines.

Primary paper: https://arxiv.org/html/2507.13023v3
Published version: https://doi.org/10.4230/LIPIcs.AFT.2025.26
Supplementary Dune dashboard: https://dune.com/rig_ef/cex-dex-dash
CEX-DEX Dune query: https://dune.com/queries/4931834
Bot labels: https://dune.com/queries/3375615
Binance historical data: https://docs.tardis.dev/historical-data-details/binance
MEV-Boost: https://docs.flashbots.net/flashbots-mev-boost/
Ultra Sound bid adjustment: https://github.com/ultrasoundmoney/docs/blob/main/bid_adjustment.md