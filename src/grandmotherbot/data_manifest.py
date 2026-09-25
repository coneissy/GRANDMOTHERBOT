from __future__ import annotations

"""Canonical source manifest for exact Wu et al. (AFT 2025) replication.

This module records the upstream observations required to reproduce the paper.
It deliberately distinguishes public source availability from local ingestion:
a URL being public is not evidence that the corresponding rows have been
downloaded.
"""

from dataclasses import dataclass
from typing import Final


PAPER = "Wu, Sui, Thiery & Pai, LIPIcs.AFT.2025.26"
START_BLOCK: Final = 17_866_488
END_BLOCK: Final = 21_998_438
START_DATE: Final = "2023-08-08"
END_DATE: Final = "2025-03-08"

# Published replication targets.
CURATED_CANDIDATES: Final = 8_723_233
MISSING_TARDIS_PRICES: Final = 163_148
INVENTORY_ADJUSTMENTS: Final = 683_539
FINAL_ARBITRAGES: Final = 7_203_560
FINAL_VOLUME_USD: Final = 241_700_000
EXTRACTED_VALUE_USD: Final = 233_800_000

@dataclass(frozen=True)
class RequiredDataset:
    id: str
    source: str
    url: str
    role: str
    access: str
    required_fields: tuple[str, ...]


DATASETS: Final[tuple[RequiredDataset, ...]] = (
    RequiredDataset(
        "dune_cex_dex_4931834",
        "Dune",
        "https://dune.com/queries/4931834",
        "Primary 8,723,233 candidate CEX-DEX transaction population",
        "public query page; result export/API access required for bulk rows",
        (
            "block_number", "block_time", "tx_hash", "tx_index",
            "from_addr", "to_addr", "mev_bot_label", "base_fees",
            "priority_fees", "cb_transfer", "mev_value", "volume",
            "token_bought_amount", "token_sold_amount", "taker",
            "token_bought_contract", "token_sold_contract",
        ),
    ),
    RequiredDataset(
        "dune_dex_trades",
        "Dune",
        "https://docs.dune.com/data-catalog/evm/ethereum/curated-data/dex/dex-trades",
        "Raw/underlying DEX trade reconstruction",
        "Dune data access",
        ("blockchain", "block_time", "tx_hash", "tx_index", "token_bought_address",
         "token_sold_address", "token_bought_amount", "token_sold_amount"),
    ),
    RequiredDataset(
        "dune_atomic_mev_3493305",
        "Dune",
        "https://dune.com/queries/3493305",
        "Exclude atomic MEV activity for Heuristic 3",
        "public query page; result access required",
        ("tx_hash",),
    ),
    RequiredDataset(
        "dune_dex_bot_labels_3375587",
        "Dune",
        "https://dune.com/queries/3375587",
        "Exclude known DEX trading bots / labeled actors for Heuristic 5",
        "public query page; result access required",
        ("address",),
    ),
    RequiredDataset(
        "flashbots_mempool_dumpster",
        "Flashbots",
        "https://mempool-dumpster.flashbots.net",
        "Determine whether candidate transactions were observed in public mempools",
        "public archive",
        ("timestamp", "hash", "sources", "includedAtBlockHeight",
         "includedBlockTimestamp", "inclusionDelayMs"),
    ),
    RequiredDataset(
        "tardis_binance_quotes",
        "Tardis",
        "https://api.tardis.dev/v1/exchanges/binance",
        "Paper CEX mid-price markouts",
        "API key / entitled historical access",
        ("timestamp", "symbol", "bid", "ask"),
    ),
    RequiredDataset(
        "tardis_binance_l2",
        "Tardis",
        "https://docs.tardis.dev/historical-data-details/binance",
        "GrandMother executable CEX liquidity extension",
        "API key / entitled historical access",
        ("timestamp", "symbol", "side", "price", "amount"),
    ),
    RequiredDataset(
        "relayscan_mevboost",
        "RelayScan",
        "https://www.relayscan.io/builder-profit",
        "MEV-Boost bids/payloads and builder attribution",
        "historical access/export required",
        ("slot", "block_number", "builder", "value", "proposer"),
    ),
    RequiredDataset(
        "ultrasound_bid_adjustments",
        "Ultra Sound Relay",
        "https://github.com/ultrasoundmoney/docs/blob/main/bid_adjustment.md",
        "Appendix G builder-profit adjustment",
        "historical relay data required",
        ("slot", "builder", "bid_adjustment_delta"),
    ),
    RequiredDataset(
        "token_universe",
        "Etherscan + CoinMarketCap",
        "https://etherscan.io/ and https://coinmarketcap.com/",
        "287 Binance-listed ERC-20 contract-address universe",
        "historical snapshot must be preserved",
        ("contract_address", "symbol"),
    ),
)


RECONCILIATION: Final = {
    "curated_candidates": CURATED_CANDIDATES,
    "missing_tardis_prices": MISSING_TARDIS_PRICES,
    "inventory_adjustments": INVENTORY_ADJUSTMENTS,
    "final_arbitrages": FINAL_ARBITRAGES,
    "final_volume_usd": FINAL_VOLUME_USD,
    "extracted_value_usd": EXTRACTED_VALUE_USD,
}

# These are NOT completion flags. They are explicit gates so CI cannot
# silently treat a source specification as an ingested dataset.
REPLICATION_GATES: Final[tuple[str, ...]] = (
    "dune_4931834_downloaded",
    "dune_4931834_schema_validated",
    "dune_4931834_row_count_reconciled",
    "mempool_public_visibility_reconstructed",
    "atomic_mev_exclusions_reproduced",
    "dex_bot_router_exclusions_reproduced",
    "tardis_quote_history_downloaded",
    "tardis_markout_grid_reproduced",
    "searcher_t_star_reestimated",
    "mevboost_payloads_downloaded",
    "ultrasound_adjustments_downloaded",
    "appendix_h_reconciled",
    "paper_headline_results_reconciled",
)

# GrandMother-only extensions. They must never replace the paper baseline.
EXTENSION_DATASETS: Final[tuple[str, ...]] = (
    "tardis_binance_l2",
    "dex_pool_state_and_liquidity_curves",
    "multi_venue_cex_execution",
    "execution_probability",
    "hedge_latency",
    "uncertainty_intervals",
    "counterfactual_scenarios",
)
