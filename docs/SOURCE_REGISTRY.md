# GrandMother Source Registry

## Canonical paper inputs

### Dune Analytics
URL: https://dune.com/home
Role: primary on-chain analytics and DEX transaction data source.

### Etherscan
URL: https://etherscan.io/
Role in the paper: cross-check ERC-20 contract addresses for Binance-listed tokens.

### CoinMarketCap
URL: https://coinmarketcap.com/
Role in the paper: cross-check Binance-listed token universe and token metadata.

The paper explicitly states that ERC-20 contract addresses for 287 Binance-listed
tokens were cross-verified using Etherscan and CoinMarketCap before being joined
against the Dune DEX trades dataset for Heuristic 6. citeturn873156view0

## GrandMother extension

### Arkham
Main URL: https://arkm.com/
Intel: https://intel.arkm.com/
Role: secondary entity and wallet attribution, address clustering, CEX wallet
cross-checks, and manual-review support.

Arkham is not substituted for the paper's Etherscan/CoinMarketCap token
verification. It is an additional attribution layer added by GrandMother.

## Evidence hierarchy

Dune -> primary empirical detection
Etherscan + CoinMarketCap -> token-list / contract verification
Arkham -> secondary entity attribution
Tardis -> historical Binance market reconstruction
Relayscan + Ultra Sound -> builder economics
Relayscan snapshots -> point-in-time builder-market observatory

Each source is retained with its role so that GrandMother can distinguish
replication inputs from extensions and avoid silently changing the paper's
baseline methodology.

## Reference-by-reference Data Center

Each supplied bibliography reference receives a numbered source artifact under:

data/reference/sources/

Reference status:

| ID | Source | Status |
| --- | --- | --- |
| 001 | Arkham | fetched and normalized |
| 002 | CoinMarketCap | fetched and normalized |
| 003 | Dune Analytics | fetched and normalized |
| 004 | Etherscan.io | fetched and normalized |
| 005 | libMEV | fetched and normalized |
| 006 | ZeroMEV | fetched and normalized |
| 007 | EIP-7782: Reduce Block Latency | fetched and normalized |
| 008 | Optimal execution of portfolio transactions | fetched and normalized |
| 009 | The Influence of CeFi-DeFi Arbitrage on Order-Flow Auction Bid Profiles | fetched and normalized |
| 010 | MEV Bid Data Explorer | fetched and normalized |
| 011 | Dune dex_aggregator.trades | fetched and normalized |
| 012 | Dune dex.trades on Ethereum | fetched and normalized |
| 013 | Stealth Trading and Volatility: Which Trades Move Prices? | fetched and normalized |
| 014 | Optimal Control of Execution Costs | fetched and normalized |
| 015 | Binance Spot Trading Fee Rate | fetched and normalized |
| 016 | MEV Blocker | fetched and normalized |
| 017 | MEV Capture and Decentralization in Execution Tickets | fetched and normalized |
| 018 | Becoming Immutable: How Ethereum is Made | fetched and normalized |
| 019 | Empirical Analysis of Cross Domain CEX <> DEX Arbitrage on Ethereum | fetched and normalized |
| 020 | A Tale of Two Arbitrages | fetched and normalized |
| 021 | A New Game in Town | fetched and normalized |
| 022 | Statistical Arbitrage on AMMs and Block Building on Ethereum Part 1 | fetched and normalized |
| 023 | Flash Boys 2.0 | fetched and normalized |
| 024 | Committee-driven MEV smoothing | fetched and normalized |
| 025 | MEV burn: a simple design | fetched and normalized |
| 026 | Does a Central Clearing Counterparty Reduce Counterparty Risk? | fetched and normalized |
| 027 | BuilderNet | fetched and normalized |
| 028 | Flashbots DEX trading bot table | fetched and normalized |
| 029 | Illuminating Ethereum's Order Flow Landscape | fetched and normalized |
| 030 | Flashbots League of Legends dashboard | fetched and normalized |
| 031 | Flashbots Mempool Dumpster | fetched and normalized |
| 032 | Flashbots MEV-Boost | fetched and normalized |
| 033 | MEV-Boost Analytics - RelayScan | fetched and normalized |
| 034 | Flashbots MEV-Share | fetched and normalized |
| 035 | Uniswap X Fillers | fetched and normalized |
| 036 | Ethereum Proof-of-Stake | fetched and normalized |
| 037 | Censorship Resistance in On-Chain Auctions | fetched and normalized |
| 038 | Measuring Arbitrage Losses and Profitability of AMM Liquidity | fetched and normalized |
| 039 | The Centralizing Effects of Private Order Flow on Proposer-Builder Separation | fetched and normalized |
| 040 | Ethereum's Proposer-Builder Separation: Promises and Realities | fetched and normalized |
| 041 | Non-Atomic Arbitrage in Decentralized Finance | fetched and normalized |
| 042 | Atomic MEV table | fetched and normalized |
| 043 | MEV Sandwich Trades | fetched and normalized |
| 044 | Competition for Retail Order Flow and Market Quality | fetched and normalized |
| 045 | Performance of Algorithmic Trading Orders: Size, Speed, and Volume | fetched and normalized |
| 046 | Angstrom | fetched and normalized |
| 047 | Automated Market Making and Arbitrage Profits in the Presence of Fees | fetched and normalized |
| 048 | Automated Market Making and Loss-Versus-Rebalancing | fetched and normalized |
| 049 | Loss-Versus-Rebalancing under Deterministic and Generalized Block-Times | fetched and normalized |
| 050 | Unity is Strength: A Formalization of Cross-Domain Maximal Extractable Value | fetched and normalized |
| 051 | Who Wins Ethereum Block Building Auctions and Why? | fetched and normalized |
| 052 | An Empirical Study of DeFi Liquidations: Incentives, Risks, and Instabilities | fetched and normalized |
| 053 | Quantifying Blockchain Extractable Value: How dark is the forest? | fetched and normalized |
| 054 | Ultra Sound Relay Bid Adjustment | fetched and normalized |
| 055 | The Limits of Arbitrage | fetched and normalized |
| 056 | CEX-DEX Bots Label List | fetched and normalized |
| 057 | CEX-DEX Transactions 202308-202503 | fetched and normalized |
| 058 | Tardis Available Token Price Data on Binance | fetched and normalized |
| 059 | Tardis Binance Spot Historical Data | fetched and normalized |
| 060 | Builder Dominance and Searcher Dependence | fetched and normalized |
| 061 | Blockchain Censorship | fetched and normalized |
| 062 | Time to Bribe: Measuring Block Construction Market | fetched and normalized |
| 063 | mevboost.pics | fetched and normalized |
| 064 | From Competition to Centralization: The Oligopoly in Ethereum Block Building Auctions | fetched and normalized |
| 065 | Strategic Bidding Wars in On-chain Auctions | fetched and normalized |
| 066 | Searcher-Builder Relationship Dashboard | fetched and normalized |
| 067 | Decentralization of Ethereum's Builder Market | fetched and normalized |
| 068 | Execution Welfare Across Solver-based DEXes | fetched and normalized |
| 069 | RediSwap: MEV Redistribution Mechanism for CFMMs | fetched and normalized |
| 070 | High-Frequency Trading on Decentralized On-Chain Exchanges | fetched and normalized |
| 071 | Cross-Chain Arbitrage: The Next Frontier of MEV in Decentralized Finance | fetched and normalized |

All 71 numbered source artifacts are present.

The numbered artifacts are the research Data Center layer. Each record separates
the source's original role from any GrandMother extension, preserves available
retrieval and version information, and identifies the GrandMother modules that
can consume the source.
