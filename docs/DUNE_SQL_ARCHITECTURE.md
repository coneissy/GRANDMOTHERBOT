# DuneSQL Architecture for GrandMother

## Purpose

DuneSQL is a Trino-based distributed query engine. Dune stores queryable data
in Parquet and uses Delta Lake for data management and versioning.

## Why this matters for GrandMother

GrandMother queries large Ethereum history tables. Query design must therefore
take advantage of Dune's physical storage behavior rather than treating each
table as an abstract row store.

## Storage and scan model

DuneSQL can prune Parquet files and row groups using column min/max statistics.
The scan proceeds through file, row group, column chunk, and page levels. The
engine reads only required column chunks and can dynamically filter work as
execution proceeds.

## Time partitioning

Dune documents time-based partitioning around block time, block date, and block
number for blockchain datasets. GrandMother should put explicit time bounds on
large scans and use block-based filters where they narrow the search.

## Delta Lake

Dune documents Delta Lake support for ACID transactions, schema evolution, time
travel, upserts/deletes, and data versioning.

For GrandMother reproducibility, this means a Dune result should be represented
by more than a URL. Where available, preserve query ID, execution ID, execution
time, query text/version, source dataset metadata, parameters, row count, and
GrandMother commit. When a source-version identifier is available, preserve it
as part of the manifest.

## Query engineering rules

1. Apply explicit study-period filters early.
2. Select only required columns from large raw tables.
3. Keep chain and time restrictions inside relevant scans and joins.
4. Preserve the exact published SQL for baseline replication.
5. Implement corrected variants separately from the frozen baseline.
6. Use incremental models when extending an already materialized historical
   dataset.
7. Record execution metadata so a later result can be distinguished from the
   original query execution.

## GrandMother implications

GM01 should maintain two query modes:

- replication mode: frozen paper SQL and original boundaries
- corrected mode: versioned fixes with explicit rationale

The two modes must never be silently mixed. Differences between them become
part of the research robustness record.

## Source

https://docs.dune.com/query-engine/dunesql-architecture