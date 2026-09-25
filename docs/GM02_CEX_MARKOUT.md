# GM02 CEX Markout: Tardis Binance Spot Implementation Specification

Status: implementation-ready

## Purpose

GM02 reconstructs Binance Spot market state around each GrandMother Ethereum CEX-DEX candidate. It produces a paper-compatible mid-price markout and an executable hedge-cost extension.

The published baseline remains distinct from the GrandMother extension:

- Baseline: native Binance bookTicker, mid-price markout.
- Extension: depthSnapshot plus depth reconstruction, executable bid/ask VWAP, spread, market impact, and configurable fees.

## Study and extraction windows

Paper replication window:

- 2023-08-08 through 2025-03-08
- Ethereum block range is frozen separately in config/paper.yaml.

Pilot extraction window:

- candidate anchor minus 1 second
- through candidate anchor plus 5 seconds

Robustness extraction window:

- candidate anchor minus 2 seconds
- through candidate anchor plus 10 seconds

All timestamps are UTC.

## Tardis feeds

### trade

Normalized fields:

- exchange
- symbol
- timestamp
- local_timestamp
- id
- side
- price
- amount

Binance raw trade events additionally preserve the native event time, trade time, trade ID, price, quantity, maker flag, and raw message.

For Binance:

- exchange_timestamp_us uses native trade time T when present.
- side is sell when buyerIsMaker/m is true, otherwise buy.

### bookTicker

Native Binance best bid and best ask feed.

Normalized fields:

- exchange
- symbol
- timestamp
- local_timestamp
- ask_amount
- ask_price
- bid_price
- bid_amount

For Binance Spot, the native bookTicker payload does not provide the documented E/T event timestamp. GM02 therefore leaves exchange_timestamp_us null and uses local_timestamp_us as the observation clock.

### depth

Binance incremental order book updates.

GM02 retains:

- first update ID U
- final update ID u
- bid updates
- ask updates
- native event time E when present
- local capture time

Binance Spot depth was collected by Tardis at the fastest available cadence for the historical period, with 100ms updates after 2019-08-30.

### depthSnapshot

Tardis-generated initial order book snapshot produced from Binance REST depth snapshots.

GM02 supports:

- lastUpdateId
- bids
- asks
- generated marker

Tardis documents snapshots up to the top 1000 levels.

## Timestamp rules

Three clocks remain separate:

1. Ethereum block_time: CEX-DEX causal anchor used by the research design.
2. Binance exchange timestamp: exchange event timestamp when supplied by the native feed.
3. Tardis local timestamp: synchronized Tardis server arrival timestamp.

Tardis timestamps every received WebSocket message at arrival time before message processing. CSV and replay ordering preserve capture order.

For equal exchange timestamps, local timestamp and row position are the tie-breakers.

Do not perform sub-millisecond causal inference across different Tardis collection regions.

## Ordering rules

Canonical event order:

(local_timestamp_us, capture_sequence)

Tardis does not guarantee cross-channel ordering between trades and order-book feeds. Therefore a trade and bookTicker event with the same exchange timestamp must not be treated as a causally ordered pair.

## L2 reconstruction

The book state is reconstructed from depthSnapshot plus depth.

Rules:

1. Ignore depth updates before the first snapshot.
2. Load snapshot bids and asks as the complete state.
3. For each depth update, amount greater than zero replaces the level quantity.
4. Amount equal to zero removes the level.
5. Require Binance sequence continuity: U <= previous_u + 1 <= u.
6. If continuity is broken, mark the state invalid and stop applying updates until the next snapshot.
7. A later snapshot resets the state and restores validity.
8. Preserve the first invalid event and the reason in QA output.

## BBO derivation

From bookTicker:

mid = (bid + ask) / 2

spread = ask - bid

spread_bps = spread / mid * 10000

From L2:

- best bid is the maximum bid price.
- best ask is the minimum ask price.

The paper baseline should use bookTicker directly rather than substituting a reconstructed quote series.

## Markout selection

Default policy:

- reference: last_at_or_before candidate_time plus selected reference offset
- target: first_at_or_after candidate_time plus horizon

Horizons:

- -1.0s through +10.0s
- step 0.5s

The exact paper matching rule can be selected explicitly if the source implementation uses a different nearest-observation rule. GM02 must not silently change this policy.

For a long exposure:

markout = (mid_target - mid_reference) / mid_reference

For a short exposure:

markout = -(mid_target - mid_reference) / mid_reference

## Executable hedge simulation

For a DEX trade that buys token A and sells token B:

- sell A on Binance using bid-side depth.
- buy B on Binance using ask-side depth.

For each leg:

VWAP = sum(price_i * quantity_i) / filled_quantity

Track:

- requested amount
- filled amount
- completeness
- VWAP
- notional
- best available price
- slippage in basis points

For an incomplete fill, do not coerce the result into a complete hedge. Preserve the shortfall.

## Fees

Tardis instrument fee fields are metadata, not a historical account-specific fee record. GM02 therefore treats the fee rate as a research configuration input.

The paper-compatible run must use the paper's documented CEX fee assumption. GrandMother robustness runs may vary this input.

## Symbol metadata

Use:

GET /v1/instruments/binance/:symbol_id

and retain both:

- id: exchange-native symbol identifier.
- datasetId: Tardis CSV dataset identifier.

Relevant metadata includes:

- baseCurrency
- quoteCurrency
- type
- listing
- availableSince
- availableTo
- priceIncrement
- amountIncrement
- minTradeAmount
- minNotional

Historical eligibility uses the instrument's availableSince and availableTo fields, not current active status alone.

## HTTP API

Base:

https://api.tardis.dev/v1

Historical feed:

/data-feeds/binance

Parameters:

- from
- offset
- filters

The endpoint returns one-minute slices based on Tardis localTimestamp boundaries. Filters are URL-encoded JSON objects with channel and optional symbols. Binance symbols must match the API format, which is lowercase.

Authenticated requests use:

Authorization: Bearer YOUR_API_KEY

Tardis recommends Accept-Encoding: gzip.

Empty lines are disconnect markers in the raw API. They are preserved by the raw client and excluded from normalized CSV exports.

## Python client

Use the maintained unified package:

pip install tardis-dev

The deprecated tardis-client package is not the GrandMother dependency.

The current package provides:

from tardis_dev import Channel, replay

The replay function accepts ISO date strings or Python datetime values. Naive datetimes are interpreted as UTC.

GM02 uses the HTTP client directly for narrow candidate windows because that interface makes minute slicing and raw disconnect markers explicit. The optional tardis-dev adapter is provided for wider historical replay and cache-backed workflows.

## CSV

Tardis normalized datasets are daily gzip CSV files.

Important properties:

- delimiter: comma
- line ending: LF
- decimal mark: dot
- timestamps: microseconds since Unix epoch
- timezone: UTC
- files are ordered and split by local_timestamp

Recommended GM02 datasets:

- trades
- book_ticker
- incremental_book_L2
- book_snapshot_25

Use Parquet as the local analytics format after extraction.

## Canonical event schema

gm02_cex_events:

- exchange
- channel
- symbol
- exchange_timestamp_us
- local_timestamp_us
- capture_sequence
- event_type
- trade_id
- book_update_id
- first_update_id
- final_update_id
- side
- price
- amount
- best_bid
- best_bid_amount
- best_ask
- best_ask_amount
- bids_json
- asks_json
- is_snapshot
- generated
- raw_message

Price and quantity are preserved as decimal strings at the raw boundary to avoid binary floating-point corruption.

## QA requirements

Every extraction run records:

- Tardis exchange details snapshot
- API key entitlement snapshot when authenticated
- requested symbols
- requested channels
- study window
- number of API minute calls
- disconnect markers
- raw event count
- normalized event count
- symbols actually observed
- channel coverage
- order book sequence failures
- missing BBO targets
- incomplete executable fills
- source artifact paths and checksums

## Research integration

GM02 output feeds GM03.

GM01 candidate -> Binance symbol map -> Tardis market window -> markout/execution -> GM03 searcher PnL

The paper replication and GrandMother robustness output must remain separately addressable.

## Primary sources

- https://docs.tardis.dev/historical-data-details/binance
- https://docs.tardis.dev/api/http-api-reference
- https://docs.tardis.dev/python-client/replaying-historical-data
- https://docs.tardis.dev/downloadable-csv-files/data-types
- https://docs.tardis.dev/api/instruments-metadata-api
- https://developers.binance.com/docs/binance-spot-api-docs/web-socket-streams
