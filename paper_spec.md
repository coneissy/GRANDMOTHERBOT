# Exact analytical specification implemented in GRANDMOTHERBOT

Source: arXiv:2507.13023v3, "Measuring CEX-DEX Extracted Value and Searcher Profitability: The Darkest of the MEV Dark Forest."

## Observation scope

- Ethereum blocks 17866488 through 21998438.
- August 8, 2023 through March 8, 2025.
- DEX trades: Dune `dex.trades`.
- Binance spot historical quotes: Tardis.dev.
- Binance-listed ERC-20 contracts: Etherscan and CoinMarketCap cross-check.
- MEV-Boost bids/payloads: relayscan.io.
- Ultra Sound bid adjustments: Ultra Sound relay.

## Identification

Require all six heuristics:

H1. Transaction is private: not seen in a public mempool before inclusion.

H2. At least one included swap is the first swap in its direction and DEX pool for the block.

H3. Transaction is not classified as atomic MEV and is not a liquidation.

H4. Transaction is not an OFA backrun.

H5. Transaction is not submitted to a known router, labeled trading bot, or bot controlling an EOA with an ENS name.

H6. No ERC-721 transfer and, after intermediate swaps are removed, the final two tokens are both listed on a major CEX such as Binance.

Appendix F removes the former 400,000-gas limit and the former coinbase-transfer / >=1 GWei-priority-fee heuristic. Appendix F.3 also applies five manual address exclusions.

## Multi-swap reconstruction

Aggregate sequential swap flows by token. Intermediate tokens cancel. The resulting net flow must contain exactly one token bought and one token sold.

## Markout valuation

Use Binance USDT-pair mid-prices and assume 1 USDT = 1 USD.

For trade i with DEX volume V_i, acquired amount x of token A, disposed amount y of token B:

MR_i(t) = x * P_A(t) - y * P_B(t) - CEX taker fees

GR_i(t) = MR_i(t) / V_i

Evaluate t in {-1.0, -0.5, 0.0, ..., 10.0} seconds.

## Optimal execution horizon

For searcher j:

t*_j = argmax_t Median_i GR_i(t)

If multiple horizons share the maximum before the return decreases, choose the largest t.

The published Table 7 contains the empirical Pattern 1/2/3 labels and t* values for the 23 labeled searchers. Pattern 3 searchers have no reliable peak in the observation window and are omitted from revenue/PnL estimation.

## Revenue, PnL, margin

Estimated EV_i = MR_i(t*_j) - base_fees_i

Estimated PnL_i = Estimated EV_i - builder_tips_i

Builder tips include priority fees and coinbase transfers.

Convert ETH base fees, priority fees, and coinbase transfers to USD with ETH-USDT mid-price at slot time.

PM_i = Estimated PnL_i / Estimated EV_i, only if Estimated EV_i > 0. Otherwise margin is N/A.

Trades whose markout revenue remains below base fees across the complete [-1,+10] window are inventory-adjustment-like and excluded from revenue/PnL estimation.

## Liquidity

Major tokens are WETH, WBTC, USDT, USDC, TUSD, FDUSD, BUSD, DAI. Remaining tokens are ALT.

Compute Major-Major, Major-ALT and ALT-ALT trade count/volume shares and relate these to the gross-return/hedge-decay patterns.

## Builder integration

A searcher is exclusive to a builder when more than 50% of its volume is sent to that builder. Otherwise it is neutral.

Compare exclusive-builder blocks with other blocks using median revenue, median margin and payment shares.

## Integrated builder correction

For block k built by builder j:

Without Ultra Sound bid adjustment:

BP_j,k = DeltaCoinbase_j,k

With Ultra Sound bid adjustment:

BP_j,k = DeltaCoinbase_j,k - b_j,k + r * delta_k

where r=1 before 2024-03-05 05:00 UTC and r=0.5 afterward.

For integrated searcher:

SP_j,k = sum(PnL_hat_i,j) over that searcher's CEX-DEX trades in block k

P_j,k = BP_j,k + SP_j,k

PM_j,k = P_j,k / (P_j,k + b_j,k - r*delta_k)

A block is subsidized only when both BP_j,k < 0 and P_j,k < 0.

## Landscape and concentration

The reproduction computes daily CEX-DEX count/volume, weekly searcher shares, weekly volume HHI, weekly extracted-value HHI, top-builder volume shares, and searcher-builder matrices.

Section 7.3 correlation analysis uses contemporaneous and lagged daily shares at 1, 3 and 7 days, including reverse-direction checks.

## Empirical limitations retained

The research cannot observe the actual off-chain CEX hedge, may miss trades, uses a single empirical t* per searcher, and does not observe off-chain rebates or OFA refunds. These limitations remain explicit in the report.
