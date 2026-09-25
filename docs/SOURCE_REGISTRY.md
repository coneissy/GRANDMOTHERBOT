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
| 003 | Dune Analytics | pending |
| 004 | Etherscan | pending |
| 005-071 | Remaining references | pending |

The numbered artifacts are the research Data Center layer. Each record should
separate the source's original role from any GrandMother extension, preserve
retrieval/version information, and identify the exact GM module that can consume
the source.
