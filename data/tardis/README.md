# GrandMother Tardis Binance Spot layer

This directory documents the paper-reproduction input contract. Raw Tardis files are intentionally not committed.

## Locked source

- Exchange: Binance Spot
- Dataset: Tardis normalized `quotes`
- Symbols: Binance USDT spot pairs
- Price: `(bid_price + ask_price) / 2`
- Time field: normalized Tardis `timestamp`; Tardis documents `local_timestamp` as the fallback when an exchange timestamp is unavailable.
- Reference clock: Ethereum slot time
- Horizons: -1.0s through +10.0s, every 0.5s, exactly 23 points
- Quote selection: last quote at or before each target timestamp
- Missing quote / unavailable day: NULL and excluded from the corresponding markout, never zero-filled
- Paper CEX taker fee: 0.01725% = 0.0001725

## Daily files

Tardis downloadable normalized files use:

`https://datasets.tardis.dev/v1/binance/quotes/YYYY/MM/DD/SYMBOL.csv.gz`

The exact files required are determined by the eligible Binance USDT symbols and the Ethereum trade dates. Do not download the entire Binance universe unnecessarily.

## Provenance

Every derived markout row should retain:

- source URL
- source file date
- symbol
- target timestamp
- quote timestamp
- quote local timestamp
- quote staleness in microseconds
- bid / ask / midpoint
- fee rate
- ingestion version

Raw Tardis files remain external/licensed inputs and are not committed to Git.
