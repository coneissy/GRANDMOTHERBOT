# Normalized input data

The paper's sources are external. The pipeline accepts normalized exports so that the analysis can be reproduced without embedding credentials.

## transactions.csv

One row per Ethereum transaction candidate.

Required columns:
`tx_hash,block_number,slot_time,from_address,observed_public_mempool,first_swap_in_pool_direction,atomic_mev,liquidation,ofa_backrun,known_router,labeled_trading_bot,ens_named_eoa_controller,erc721_transfer,final_pair_major_cex_listed,searcher_label,builder`

Additional swap rows belong in `swaps.csv`.

## swaps.csv

One row per swap log in a transaction.

Required columns:
`tx_hash,log_index,dex,pool,token_in,token_out,amount_in,amount_out`

The reconstruction stage aggregates sequential swap flows by token and reduces intermediate tokens.

## markouts.csv

One row for every available trade/horizon price observation.

Required columns:
`tx_hash,horizon_s,token_a_usdt_mid,token_b_usdt_mid,cex_taker_fees_usd,dex_volume_usd`

For profitability estimation also provide:
`amount_a,amount_b,base_fees_usd,builder_tips_usd`

Expected horizons are exactly -1.0 through +10.0 seconds in 0.5-second increments.

## builder_blocks.csv

One row per winning block used by Appendix G.

Preferred raw/ETH fields, matching the paper's calculation order:
`block_number,builder,slot_time,delta_coinbase_eth,bid_value_eth,bid_adjusted,bid_adjustment_delta_eth,eth_usdt_mid,searcher_pnl_usd,ofa_refund_usd`

The paper computes builder profit in ETH:
- without Ultra Sound adjustment: DeltaCoinbase
- with adjustment: DeltaCoinbase - original bid + refund_rate * adjustment delta

Then converts that ETH builder profit to USD using the ETH-USDT mid-price at the corresponding slot time.

For pre-normalized inputs, the legacy USD fields
`delta_coinbase_usd,bid_value_usd,bid_adjustment_delta_usd`
remain supported, but they are a convenience path rather than the preferred raw representation.

Ultra Sound refund rate is 100% before 2024-03-05 05:00 UTC and 50% after that cutoff.

## cex_tokens.csv

One row per Binance-listed ERC-20 contract.

Required columns:
`symbol,contract_address,source`

Use the cross-checked contract addresses, not symbols alone.

## GM02 Tardis market data

GM02 consumes Binance Spot Tardis historical data and preserves the distinction between exchange timestamps and Tardis capture timestamps.

### Recommended raw feeds

- `trade`: individual Binance executions
- `bookTicker`: native best bid/ask
- `depth`: incremental L2 updates
- `depthSnapshot`: Tardis-generated initial order-book snapshots

### Canonical normalized event

The extractor stores:

`exchange,channel,symbol,exchange_timestamp_us,local_timestamp_us,capture_sequence,event_type,trade_id,book_update_id,first_update_id,final_update_id,side,price,amount,best_bid,best_bid_amount,best_ask,best_ask_amount,bids_json,asks_json,is_snapshot,generated,raw_message`

The canonical ordering key is:
`(local_timestamp_us,capture_sequence)`.

For Binance `bookTicker`, the native payload has no documented event timestamp, so `exchange_timestamp_us` remains null and `local_timestamp_us` is the observation clock.

### GM02 source policy

Paper-compatible baseline:
`bookTicker -> mid-price markout`

Execution-cost extension:
`depthSnapshot + depth -> reconstructed book -> executable VWAP`

### Storage

Use Parquet for normalized events once the optional `parquet` extra is installed:

```bash
pip install -e ".[tardis,parquet]"
```

Raw Tardis JSON should remain auditable and should never contain API credentials.

## GM02 CLI

Check the Tardis entitlement and Binance dataset metadata:

```bash
grandmother-paper tardis-key-info
grandmother-paper tardis-binance
```

Fetch a narrow historical pilot window:

```bash
export TARDIS_API_KEY="..."
grandmother-paper tardis-fetch \
  --start 2024-01-14T00:00:00Z \
  --end 2024-01-14T00:00:10Z \
  --symbols BTCUSDT ETHUSDT \
  --channels trade bookTicker \
  --output data/tardis/pilot.ndjson
```

For canonical Parquet:

```bash
grandmother-paper tardis-fetch \
  --start 2024-01-14T00:00:00Z \
  --end 2024-01-14T00:00:10Z \
  --symbols BTCUSDT ETHUSDT \
  --channels trade bookTicker depth depthSnapshot \
  --output data/tardis/pilot.parquet
```

Do not paste a Tardis API key into SQL, notebooks, Git, issue comments, or source code.

## Paper period

Block 17,866,488 through 21,998,438.
2023-08-08 through 2025-03-08.
