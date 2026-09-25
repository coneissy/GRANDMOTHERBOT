# GrandMother v1 gap closure

The existing Python package is a faithful research reproduction of arXiv:2507.13023v3. It is not itself a live trading system. The production path therefore keeps the paper methodology as an evidence/reference layer and adds a separate execution model.

## Closed gaps

1. Markout grid and searcher horizon: exact -1.0 to +10.0 second grid at 0.5-second spacing, median gross-return curve, latest-horizon tie break, Pattern-3/no-horizon handling, and inventory-adjustment exclusion.
2. Live hedge realism: the paper uses Binance USDT mid-prices for historical estimation, while GrandMother live simulation walks CEX bid depth to sell acquired token A and ask depth to repurchase token B, charging taker fees on both legs.
3. DEX execution realism: constant-product exact-in quoting with pool fee and explicit gas cost. The database also stores richer pool state for concentrated-liquidity and multi-hop routing.
4. Execution uncertainty: inclusion probability and hedge-fill probability are explicit. Failed-opportunity cost is explicit rather than silently assuming 100% execution.
5. Builder/PBS context: builder bids and block observations are separate from searcher P&L, and the schema can ingest ePBS-era observations without treating them as identical to historical MEV-Boost fields.
6. Realized P&L: execution attempts, fills, and a ledger are separate from simulations. Model-comparison records expected-vs-realized error.

## Important accounting boundary

GrandMother preserves these measurements as separate states:

- observed on-chain fact
- historical estimated EV/PnL
- live simulated EV/PnL
- submitted execution
- realized P&L

A theoretical markout estimate must never be reported as realized money.

## Remaining production adapters

- Ethereum JSON-RPC/WS collector
- Binance WebSocket order-book collector
- PostgreSQL/Redis persistence
- DEX-specific state readers and multi-hop route simulator
- private submission adapter
- inclusion/fill reconciler
- realized-P&L reconciliation worker

Those adapters require live endpoints and runtime integration. The core economics, simulation contract, and storage contract are now explicit so those adapters can be implemented without changing the accounting model.
