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
001 | Arkham | fetched and normalized |
002 | CoinMarketCap | fetched and normalized |
003 | Dune Analytics | fetched and normalized |
004 | Etherscan | fetched and normalized |
005 | Reference 005 | fetched and normalized |
006 | Reference 006 | fetched and normalized |
007 | Reference 007 | fetched and normalized |
008 | Reference 008 | fetched and normalized |
009 | Reference 009 | fetched and normalized |
010 | Reference 010 | fetched and normalized |
011 | Reference 011 | fetched and normalized |
012 | Reference 012 | fetched and normalized |
013 | Reference 013 | fetched and normalized |
014 | Reference 014 | fetched and normalized |
015 | Reference 015 | fetched and normalized |
016 | Reference 016 | fetched and normalized |
017 | Reference 017 | fetched and normalized |
018 | Reference 018 | fetched and normalized |
019 | Reference 019 | fetched and normalized |
020 | Reference 020 | fetched and normalized |
021 | Reference 021 | fetched and normalized |
022 | Reference 022 | fetched and normalized |
023 | Reference 023 | fetched and normalized |
024 | Reference 024 | fetched and normalized |
025 | Reference 025 | fetched and normalized |
026 | Reference 026 | fetched and normalized |
027 | Reference 027 | fetched and normalized |
028 | Reference 028 | fetched and normalized |
029 | Reference 029 | fetched and normalized |
030 | Reference 030 | fetched and normalized |
031 | Reference 031 | fetched and normalized |
032 | Reference 032 | fetched and normalized |
033 | Reference 033 | fetched and normalized |
034 | Reference 034 | fetched and normalized |
035 | Reference 035 | fetched and normalized |
036 | Reference 036 | fetched and normalized |
037 | Reference 037 | fetched and normalized |
038 | Reference 038 | fetched and normalized |
039 | Reference 039 | fetched and normalized |
040 | Reference 040 | fetched and normalized |
041 | Reference 041 | fetched and normalized |
042 | Reference 042 | fetched and normalized |
043 | Reference 043 | fetched and normalized |
044 | Reference 044 | fetched and normalized |
045 | Reference 045 | fetched and normalized |
046 | Reference 046 | fetched and normalized |
047 | Reference 047 | fetched and normalized |
048 | Reference 048 | fetched and normalized |
049 | Reference 049 | fetched and normalized |
050 | Reference 050 | fetched and normalized |
051 | Reference 051 | fetched and normalized |
052 | Reference 052 | fetched and normalized |
053 | Reference 053 | fetched and normalized |
054 | Reference 054 | fetched and normalized |
055 | Reference 055 | fetched and normalized |
056 | Reference 056 | fetched and normalized |
057 | Reference 057 | fetched and normalized |
058 | Reference 058 | fetched and normalized |
059 | Reference 059 | fetched and normalized |
060 | Reference 060 | fetched and normalized |
061 | Reference 061 | fetched and normalized |
062 | Reference 062 | fetched and normalized |
063 | Reference 063 | fetched and normalized |
064 | Reference 064 | fetched and normalized |
065 | Reference 065 | fetched and normalized |
066 | Reference 066 | fetched and normalized |
067 | Reference 067 | fetched and normalized |
068 | Reference 068 | fetched and normalized |
069 | Reference 069 | fetched and normalized |
070 | Reference 070 | fetched and normalized |
071 | Reference 071 | fetched and normalized |

The numbered artifacts are the research Data Center layer. Each record should
separate the source's original role from any GrandMother extension, preserve
retrieval/version information, and identify the exact GM module that can consume
the source.
