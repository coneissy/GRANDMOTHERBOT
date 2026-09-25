# GrandMother Arkham Attribution Layer

## Purpose

GrandMother uses Arkham as a secondary blockchain-intelligence source for
address and entity attribution, wallet labels, tags, and transaction-flow
cross-checks.

Arkham describes its data model as addresses, entities, labels, and tags.
Its documentation also states that attribution is confidence-scored rather
than binary, and that its intelligence can change as new findings are made.

## Research role

Arkham is not a replacement for GM01 primary Dune transaction detection.

Use Arkham for:
- secondary searcher and entity attribution
- CEX wallet and deposit-address cross-checks
- builder or infrastructure address cross-checks
- entity-level clustering of related addresses
- identifying candidate addresses that require manual review
- fund-flow context where the available Arkham data supports the relevant time window

Do not use an Arkham label by itself as proof that an address is a searcher,
builder, exchange, or other actor. Preserve the attribution source, label,
entity, tag, confidence information when available, and retrieval timestamp.

## Living-intelligence rule

Arkham describes its intelligence as living intelligence. Therefore a current
API response must not silently overwrite a historical research label.

GrandMother should retain:
- source = Arkham
- retrieval_timestamp
- address
- chain
- entity
- label
- tags
- confidence, when supplied
- API or dataset version, when available

For replication of the paper period, historical labels should be compared
against the original paper/Dune label source rather than substituted without
a documented robustness specification.

## Join policy

Canonical key: lowercase(chain, address)

Recommended evidence graph:
GM01 candidate -> primary Dune attribution -> Arkham secondary attribution
-> agreement or disagreement flag -> manual review when material.

This is an evidence-resolution layer, not a profitability classifier.

## Current API relevance

Arkham provides address intelligence and related blockchain data. Its
September 8, 2026 update says the address-intelligence updates feed can report
new, updated, and deleted intelligence within minutes and supports cursor-based
pagination.

For GrandMother, this is useful for maintaining a provenance-aware current
label feed, while historical replication remains anchored to dated research
sources.

## Sources

Arkham: https://arkm.com/
Arkham API guide: https://arkm.com/docs
Arkham API: https://arkm.com/api
Arkham real-time intelligence update:
https://info.arkm.com/announcements/arkham-api-upgrade-real-time-intel
