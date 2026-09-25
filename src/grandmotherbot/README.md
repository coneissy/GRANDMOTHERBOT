# GrandMother

GrandMother is a CEX-DEX arbitrage research engine. The published-paper replication layer remains separate and frozen; this package adds venue-neutral executable economics.

Truth levels: observed, reconstructed, estimated, counterfactual.

DEX and CEX expose the same economic interface: executable quantity, price, fees, impact, capacity, execution probability and evidence. Their mechanics remain venue-specific.

The engine does not fabricate historical Dune, Tardis, MEV-Boost or Ultra Sound observations. Adapters consume supplied normalized datasets and reconcile against published benchmark counts.
