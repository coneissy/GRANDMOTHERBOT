# GrandMother Cross-Chain Activity Layer

## Purpose

This module preserves the supplied LayerZero Endpoint_call_send query as an
exact source artifact and converts the result into a canonical cross-chain
activity fingerprint.

The LayerZero query counts successful sends by sender across Arbitrum,
Avalanche C, BNB Chain, Ethereum, Optimism, Polygon, and Fantom. It is an
activity detector, not a cross-chain arbitrage detector.

## Canonical event

Each successful send is represented as:

sender, call_block_time, src_chain_id, dst_chain_id, tx_hash

The original query does not project tx_hash in the final result, so the
repository preserves it as a separate exact-source artifact.

## Derived profile

GrandMother derives:

sender, user_tx_count, unique_source_chains, unique_destination_chains,
unique_chain_pairs, first_activity, last_activity

These features are appropriate for candidate fingerprinting and confounder
controls. They can help identify whether a searcher address has activity on
multiple chains and which routes it has touched.

They do not establish that:

- a specific Ethereum CEX-DEX arbitrage was funded by a bridge;
- a LayerZero send was the hedge leg;
- cross-chain activity caused searcher profitability.

## Join policy

The canonical join key is a normalized lowercase EVM address:

GM01 candidate.from_address -> cross_chain_profile.sender

For time-aware analyses, lifetime profiles must not be joined directly as
historical explanatory variables. GrandMother should derive pre-event or
rolling features such as:

- prior 30-day LayerZero sends
- prior 7-day LayerZero sends
- distinct chains observed before the candidate block
- days since first observed cross-chain activity

This prevents look-ahead leakage in predictive or causal specifications.

## Research integration

Cross-chain features enter GrandMother as a fingerprint and confounder
layer:

GM01 detection -> searcher attribution -> cross-chain profile
-> robustness / confounder analysis

They do not change the baseline CEX-DEX identification rule.

The separate RIG paper is useful at the GM04 layer because it studies strategic
builder bidding in MEV-Boost auctions and explicitly analyzes how network
connectivity and access to MEV opportunities affect bidding incentives.

## Provenance

Source: user-supplied Dune SQL based on LayerZero Endpoint_call_send tables.
