-- GrandMother operational schema.
-- Historical paper-replication tables remain separate under data/input.
-- This schema covers live observation, simulation, execution evidence, and realized P&L.

create extension if not exists pgcrypto;

create table if not exists tokens (
    chain_id bigint not null,
    address text not null,
    symbol text,
    decimals integer,
    is_cex_listed boolean not null default false,
    cex_symbol text,
    created_at timestamptz not null default now(),
    primary key (chain_id, address)
);

create table if not exists dex_pools (
    pool_id text primary key,
    chain_id bigint not null,
    dex text not null,
    token0_address text not null,
    token1_address text not null,
    fee_bps numeric(12,6),
    pool_type text,
    active boolean not null default true,
    metadata jsonb not null default '{}'::jsonb
);

create table if not exists dex_pool_snapshots (
    pool_id text not null references dex_pools(pool_id),
    observed_at timestamptz not null,
    block_number bigint,
    block_hash text,
    reserve0 numeric(78,30),
    reserve1 numeric(78,30),
    sqrt_price_x96 numeric(78,0),
    liquidity numeric(78,30),
    tick bigint,
    raw_state jsonb not null default '{}'::jsonb,
    source text not null,
    ingested_at timestamptz not null default now(),
    primary key (pool_id, observed_at)
);

create table if not exists cex_quotes (
    venue text not null,
    symbol text not null,
    observed_at timestamptz not null,
    bid numeric(38,18),
    ask numeric(38,18),
    bid_size numeric(38,18),
    ask_size numeric(38,18),
    fee_rate numeric(18,10),
    source text not null,
    sequence_id bigint,
    ingested_at timestamptz not null default now(),
    primary key (venue, symbol, observed_at)
);

create table if not exists cex_orderbook_levels (
    venue text not null,
    symbol text not null,
    observed_at timestamptz not null,
    side text not null check (side in ('bid','ask')),
    price numeric(38,18) not null,
    quantity numeric(38,18) not null,
    level_index integer not null,
    source text not null,
    primary key (venue, symbol, observed_at, side, level_index)
);

create table if not exists chain_blocks (
    chain_id bigint not null,
    block_number bigint not null,
    block_hash text not null,
    parent_hash text,
    slot bigint,
    slot_time timestamptz,
    base_fee_wei numeric(78,0),
    proposer text,
    builder text,
    source text not null,
    observed_at timestamptz not null,
    primary key (chain_id, block_number)
);

create table if not exists builder_bids (
    chain_id bigint not null,
    slot bigint not null,
    builder text not null,
    bid_value_wei numeric(78,0),
    block_hash text,
    bid_time timestamptz,
    source text not null,
    raw_payload jsonb not null default '{}'::jsonb,
    primary key (chain_id, slot, builder)
);

create table if not exists dex_swaps (
    chain_id bigint not null,
    tx_hash text not null,
    log_index integer not null,
    block_number bigint,
    pool_id text,
    token_in text,
    token_out text,
    amount_in numeric(78,30),
    amount_out numeric(78,30),
    observed_at timestamptz,
    source text not null,
    primary key (chain_id, tx_hash, log_index)
);

create table if not exists opportunities (
    opportunity_id uuid primary key default gen_random_uuid(),
    detected_at timestamptz not null,
    chain_id bigint not null,
    searcher_address text,
    token_a text not null,
    token_b text not null,
    dex_route jsonb not null,
    cex_venue text not null,
    cex_symbol_a text,
    cex_symbol_b text,
    amount_a numeric(78,30),
    amount_b numeric(78,30),
    gross_edge_usd numeric(38,18),
    gross_edge_bps numeric(24,12),
    source_snapshot_time timestamptz,
    state_version text,
    confidence numeric(12,8),
    status text not null default 'detected',
    created_at timestamptz not null default now()
);

create table if not exists simulations (
    simulation_id uuid primary key default gen_random_uuid(),
    opportunity_id uuid not null references opportunities(opportunity_id),
    simulated_at timestamptz not null default now(),
    size_usd numeric(38,18),
    dex_fee_usd numeric(38,18),
    gas_usd numeric(38,18),
    cex_fee_usd numeric(38,18),
    slippage_usd numeric(38,18),
    builder_tip_usd numeric(38,18),
    net_if_included_usd numeric(38,18),
    inclusion_probability numeric(12,8),
    hedge_fill_probability numeric(12,8),
    expected_pnl_usd numeric(38,18),
    expected_edge_bps numeric(24,12),
    markout_horizon_s numeric(12,4),
    model_version text not null,
    assumptions jsonb not null default '{}'::jsonb
);

create table if not exists execution_attempts (
    execution_id uuid primary key default gen_random_uuid(),
    opportunity_id uuid not null references opportunities(opportunity_id),
    submitted_at timestamptz,
    submission_method text,
    target text,
    tx_hash text,
    bundle_hash text,
    nonce bigint,
    status text not null,
    failure_reason text,
    simulation_id uuid references simulations(simulation_id),
    created_at timestamptz not null default now()
);

create table if not exists fills (
    fill_id uuid primary key default gen_random_uuid(),
    execution_id uuid not null references execution_attempts(execution_id),
    venue text not null,
    symbol text not null,
    side text not null check (side in ('buy','sell')),
    quantity numeric(78,30) not null,
    price numeric(38,18) not null,
    fee_usd numeric(38,18) not null default 0,
    filled_at timestamptz not null,
    external_id text,
    source text not null
);

create table if not exists pnl_ledger (
    ledger_id uuid primary key default gen_random_uuid(),
    execution_id uuid references execution_attempts(execution_id),
    opportunity_id uuid references opportunities(opportunity_id),
    event_type text not null,
    asset text,
    quantity numeric(78,30),
    usd_value numeric(38,18),
    fee_usd numeric(38,18) not null default 0,
    realized_at timestamptz not null,
    source text not null,
    provenance jsonb not null default '{}'::jsonb
);

create table if not exists model_comparisons (
    comparison_id uuid primary key default gen_random_uuid(),
    opportunity_id uuid,
    simulation_id uuid references simulations(simulation_id),
    expected_pnl_usd numeric(38,18),
    realized_pnl_usd numeric(38,18),
    error_usd numeric(38,18),
    error_bps numeric(24,12),
    measured_at timestamptz not null default now(),
    model_version text not null
);

create index if not exists idx_cex_quotes_symbol_time on cex_quotes(venue, symbol, observed_at desc);
create index if not exists idx_dex_snapshots_pool_time on dex_pool_snapshots(pool_id, observed_at desc);
create index if not exists idx_swaps_tx on dex_swaps(chain_id, tx_hash);
create index if not exists idx_opportunities_detected on opportunities(detected_at desc);
create index if not exists idx_simulations_opportunity on simulations(opportunity_id, simulated_at desc);
create index if not exists idx_pnl_execution on pnl_ledger(execution_id, realized_at);
