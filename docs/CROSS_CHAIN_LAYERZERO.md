# GrandMother Cross-Chain Activity Layer

## Arbitrum transaction join

The supplied SQL joins layerzero_arbitrum.Endpoint_call_send.call_tx_hash
to arbitrum.transactions.hash and takes arbitrum.transactions.from as the
initiating sender.

Dune documents arbitrum.transactions as the raw transaction table for every
Arbitrum transaction, including from, to, value, gas, calldata, and receipt
status. This is the transaction-layer source for recovering the sender
associated with the LayerZero call.

## Canonical source artifacts

- data/reference/layerzero_send_original.sql
- data/reference/dune_data_catalog.yaml

## Interpretation

LayerZero activity is a cross-chain activity fingerprint, not proof that a
specific Ethereum CEX-DEX arbitrage was funded by a bridge or that a LayerZero
send was the hedge leg.

## Join policy

GM01 candidate.from_address -> cross_chain_profile.sender

LayerZero Endpoint_call_send.call_tx_hash -> chain.transactions.hash

chain.transactions.from supplies the transaction initiator.

For time-aware analysis, use pre-event or rolling features to avoid look-ahead
leakage. Do not treat lifetime cross-chain activity as contemporaneous evidence.

## Provenance

Arbitrum transactions:
https://dune.com/data/arbitrum.transactions

Arbitrum transactions documentation:
https://docs.dune.com/data-catalog/evm/arbitrum/raw/transactions

## Supplied sender-activity snapshot

GrandMother also preserves the user-supplied aggregate LayerZero sender snapshot at:

data/reference/layerzero_sender_activity_snapshot.csv

Snapshot fields:

sender, user_tx_count

Snapshot size: 25 senders.
Aggregate successful-send count across those rows: 1,755.
Mean successful sends per sender: 70.2.
Median: 56.
Minimum: 5.
Maximum: 218.

These are descriptive counts from the supplied snapshot. They are not profitability,
arbitrage, or causal scores, and they must not be interpreted as such.

The snapshot should be joined to the canonical cross-chain event/profile layer by
lowercased sender address. When a time-aware analysis is required, regenerate
features directly from timestamped LayerZero events rather than treating this
aggregate snapshot as historically contemporaneous.
