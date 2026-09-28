# GrandMother Methodology Lock

Status: LOCKED
Baseline: Wu et al., arXiv:2507.13023v3
Lock date: 2026-09-28

## Non-negotiable baseline

The exact paper-replication path remains authoritative for:
- candidate population and heuristic filtering;
- CEX mid-price markouts;
- inventory adjustments;
- MR, EV, builder-tip and PnL accounting;
- paper reconciliation targets.

GrandMother extensions MUST NOT silently replace the baseline.

## Locked extensions

1. Empirical block intervals, preserving observed event time rather than assuming constant blocks.
2. Price-jump regime classification, kept separate from ordinary/diffusive observations.
3. CEX executable liquidity and execution-cost accounting.
4. Separate paper, markout and executable profit views.
5. LVR/RVR-style AMM diagnostics kept separate from searcher profitability.
6. Builder auction observations including builder, relay, bid, exclusivity/integrated flow and optional latency.
7. Provenance and executable contract verification.
8. Dune raw/curated/aggregator evidence remains traceable.
9. Searcher/builder attribution carries evidence rather than assuming mined-block observation is complete.

## Verification rule

A component is not considered verified because an LLM, benchmark score, unit-test count, or aggregate metric says it is correct. It must satisfy an explicit contract and have executable evidence.

Critical failures are fail-closed.

## Data separation

Paper baseline: paper_replication

Execution-aware extension: executable_extension

These datasets and result views must remain separately identifiable so that execution frictions cannot contaminate the published replication.

## Research sources

- arXiv:2507.13023v3, CEX-DEX extracted value and searcher profitability.
- Ethereum builder-auction research from Robust Incentives Group.
- Dune curated DEX and aggregator data documentation.
- Tardis Binance historical market data.
- Flashbots/MEV-Boost ecosystem data and documentation.

This file is a contract, not a claim that every external dataset has already been downloaded. Acquisition remains governed by the replication gates in data_manifest.py.
