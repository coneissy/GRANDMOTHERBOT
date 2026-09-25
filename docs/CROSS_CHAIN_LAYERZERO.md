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
