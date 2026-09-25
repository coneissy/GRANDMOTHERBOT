# GRANDMOTHERBOT

GrandMother is split into two deliberately separate layers:

1. **Research reproduction**: a clean-room implementation of arXiv:2507.13023v3, preserving the paper's identification, markout, searcher-horizon, EV/PnL, liquidity, and builder analysis.
2. **Operational engine**: a Rust core for executable CEX-DEX simulation, plus a PostgreSQL schema for live observations, opportunities, executions, fills, and realized P&L.

The research layer is evidence and calibration. The operational layer must never treat a historical markout estimate as realized money.

## Research scope

- Ethereum CEX-DEX transaction identification with Heuristics 1-6.
- Multi-swap reconstruction of effective trades.
- Binance-listed token cross-checks and manual exclusions.
- Historical Binance/Tardis markouts.
- Markout horizons -1.0s to +10.0s at 0.5s.
- Markout Revenue, Gross Return, searcher-specific optimal horizon.
- Pattern-3 handling and inventory-adjustment exclusion.
- Estimated Extracted Value, searcher PnL, and profit margin.
- Major / ALT liquidity analysis.
- Searcher-builder exclusivity and builder profit correction.
- Landscape statistics, HHI, and reproduction fixtures.

## Operational engine

The new Rust engine under engine/ adds:

- exact paper markout horizon generation and median-return horizon selection;
- depth-aware CEX hedging using bids for acquired inventory and asks for repurchase inventory;
- both CEX hedge legs charged with taker fees;
- constant-product DEX exact-in quoting with pool fee;
- explicit gas, builder tip, slippage, inclusion probability, and hedge-fill probability;
- expected PnL distinct from PnL conditional on successful inclusion.

The PostgreSQL contract is in db/grandmother_schema.sql and separates:

- Ethereum blocks and builder bids;
- DEX pool state and swaps;
- CEX quotes and order-book levels;
- opportunities and simulations;
- execution attempts and fills;
- realized P&L ledger;
- expected-vs-realized model error.

## Reproduction

Put normalized data files into data/input/ using the schemas in data/README.md, then:

```bash
python -m pip install -e .[dev]
pytest
python -m grandmotherbot_paper.cli validate
python -m grandmotherbot_paper.cli analyze --input data/input --output output
```

For the Rust engine:

```bash
cargo test --manifest-path engine/Cargo.toml
```

No API credentials or private keys are stored in this repository.

## Production boundary

The next adapters are intentionally not hidden inside the accounting model:

- Ethereum JSON-RPC/WebSocket ingestion;
- Binance WebSocket order-book and authenticated execution streams;
- PostgreSQL/Redis persistence;
- DEX-specific state readers and multi-hop routing;
- private submission;
- inclusion/fill reconciliation;
- realized-P&L reconciliation.

This separation keeps the research methodology auditable while allowing the live execution system to use executable prices and actual fills rather than mid-price assumptions.
