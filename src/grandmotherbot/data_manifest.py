from __future__ import annotations

"""Canonical source manifest for exact Wu et al. (AFT 2025) replication.

Public links are evidence of source identity, not evidence that GrandMother has
downloaded the underlying rows. Every dataset therefore has an explicit
acquisition state and replication gate.
"""

from dataclasses import dataclass
from typing import Final


PAPER = "Wu, Sui, Thiery & Pai, LIPIcs.AFT.2025.26"
START_BLOCK: Final = 17_866_488
END_BLOCK: Final = 21_998_438
START_DATE: Final = "2023-08-08"
END_DATE: Final = "2025-03-08"

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
    paper_reference: str | None = None


DATASETS: Final[tuple[RequiredDataset, ...]] = (
    RequiredDataset(
        "dune_cex_dex_4931834", "Dune",
        "https://dune.com/queries/4931834",
        "Primary 8,723,233 candidate CEX-DEX population",
        "public query page; bulk result export/API required",
        ("block_number","block_time","tx_hash","tx_index","from_addr","to_addr",
         "mev_bot_label","base_fees","priority_fees","cb_transfer","mev_value",
         "volume","token_bought_amount","token_sold_amount","taker",
         "token_bought_contract","token_sold_contract"),
        "Appendix A.2 / Table 6; Ref. 49",
    ),
    RequiredDataset(
        "dune_dex_trades", "Dune",
        "https://docs.dune.com/data-catalog/evm/ethereum/curated-data/dex/dex-trades",
        "Underlying DEX trade reconstruction",
        "Dune data access",
        ("blockchain","block_time","tx_hash","tx_index","token_bought_address",
         "token_sold_address","token_bought_amount","token_sold_amount"),
        "Ref. 9 / Ref. 11 in paper versions",
    ),
    RequiredDataset(
        "dune_dex_aggregator_trades", "Dune",
        "https://docs.dune.com/data-catalog/evm/ethereum/curated-data/dex/dex-aggregator-trades",
        "Identify aggregator/OFA and router-mediated execution",
        "Dune data access",
        ("blockchain","tx_hash","project","token_bought_address",
         "token_sold_address","token_bought_amount","token_sold_amount"),
        "Appendix F / paper Ref. 10",
    ),
    RequiredDataset(
        "dune_atomic_mev_3493305", "Dune",
        "https://dune.com/queries/3493305",
        "Atomic-MEV exclusion for Heuristic 3",
        "public query page; result access required",
        ("tx_hash",),
        "Appendix F / paper Ref. 39",
    ),
    RequiredDataset(
        "dune_dex_bot_labels_3375587", "Dune",
        "https://dune.com/queries/3375587",
        "Flashbots DEX trading-bot labels for Heuristic 5",
        "public query page; result access required",
        ("address",),
        "paper Ref. 24",
    ),
    RequiredDataset(
        "dune_cex_dex_bot_labels_3375615", "Dune",
        "https://dune.com/queries/3375615",
        "CEX-DEX bot label list cited in the appendix/reference material",
        "public query page; verify exact version before baseline use",
        ("address",),
        "Appendix A.2 source list",
    ),
    RequiredDataset(
        "flashbots_mempool_dumpster", "Flashbots",
        "https://github.com/flashbots/mempool-dumpster",
        "Public-mempool absence test for Heuristic 1",
        "public Parquet/CSV archive",
        ("timestamp","hash","sources","includedAtBlockHeight",
         "includedBlockTimestamp","inclusionDelayMs"),
        "paper Ref. 26 / Heuristic 1",
    ),
    RequiredDataset(
        "tardis_binance_available_tokens", "Tardis",
        "https://api.tardis.dev/v1/exchanges/binance",
        "Verify historical availability of required Binance symbols",
        "API entitlement required",
        ("symbol",),
        "paper Ref. 50 / Appendix A.2",
    ),
    RequiredDataset(
        "tardis_binance_quotes", "Tardis",
        "https://docs.tardis.dev/historical-data-details/binance",
        "Paper CEX mid-price markouts",
        "API entitlement required",
        ("timestamp","symbol","bid","ask"),
        "paper Ref. 51 / Appendix A.2",
    ),
    RequiredDataset(
        "tardis_binance_l2", "Tardis",
        "https://docs.tardis.dev/historical-data-details/binance",
        "GrandMother executable CEX liquidity extension",
        "API entitlement required",
        ("timestamp","symbol","side","price","amount"),
        "GrandMother extension only",
    ),
    RequiredDataset(
        "mev_bid_data_explorer", "Data Always / Dune",
        "https://dune.com/data_always/mev-bid-data-explorer?block_number_t72e94=22196045",
        "Cross-check MEV-Boost bid observations",
        "public dashboard; underlying query access may vary",
        ("slot","builder","bid_value"),
        "paper Ref. 8",
    ),
    RequiredDataset(
        "relayscan_mevboost", "RelayScan",
        "https://www.relayscan.io/builder-profit?t=7d",
        "MEV-Boost payload/builder/proposer history",
        "historical access/export required",
        ("slot","block_number","builder","value","proposer"),
        "paper Ref. 28",
    ),
    RequiredDataset(
        "ultrasound_bid_adjustments", "Ultra Sound Relay",
        "https://github.com/ultrasoundmoney/docs/blob/main/bid_adjustment.md",
        "Appendix G bid-adjustment correction",
        "historical relay records required",
        ("slot","builder","bid_adjustment_delta"),
        "paper Ref. 46",
    ),
    RequiredDataset(
        "mevshare", "Flashbots",
        "https://docs.flashbots.net/flashbots-protect/mev-share",
        "Context for protected/private orderflow and bundle classification",
        "public documentation; transaction data is separate",
        ("tx_hash","bundle_id"),
        "paper Ref. 29",
    ),
    RequiredDataset(
        "uniswap_x_fillers_4050099", "Dune",
        "https://dune.com/queries/4050099",
        "Manual exclusion verification for Uniswap X fillers/solvers",
        "public query page; result access required",
        ("address","tx_hash"),
        "Appendix F / paper Ref. 33",
    ),
    RequiredDataset(
        "token_universe", "Etherscan + CoinMarketCap",
        "https://etherscan.io/ ; https://coinmarketcap.com/",
        "287 Binance-listed ERC-20 contract-address universe",
        "historical snapshot must be preserved",
        ("contract_address","symbol"),
        "Heuristic 6 / Appendix A.2",
    ),
    RequiredDataset(
        "mevblocker", "MEV Blocker",
        "https://mevblocker.io/",
        "Context/source for protected orderflow and OFA classification",
        "public service/documentation; historical transaction data separate",
        ("tx_hash","bundle_id"),
        "paper Ref. 13",
    ),
    RequiredDataset(
        "libmev", "libMEV",
        "https://libmev.com/",
        "Independent MEV/searcher cross-check and address labels",
        "public dashboard/API availability varies",
        ("searcher","address","profit","volume"),
        "paper Ref. 4",
    ),
    RequiredDataset(
        "zeromev", "ZeroMEV",
        "https://zeromev.org/",
        "Independent atomic-MEV classification cross-check",
        "public service/data availability varies",
        ("tx_hash","mev_type"),
        "paper Ref. 5",
    ),
    RequiredDataset(
        "frontier_builder_dependence", "Frontier Research",
        "https://frontier.tech/builder-dominance-and-searcher-dependence",
        "External builder/searcher relationship cross-check",
        "public article",
        ("builder","searcher"),
        "paper Ref. 52",
    ),
    RequiredDataset(
        "mevboost_pics", "MEVBoost.pics",
        "https://mevboost.pics/",
        "Builder/relay market-share cross-check",
        "public dashboard",
        ("slot","builder","relay","market_share"),
        "paper Ref. 55",
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


REPLICATION_GATES: Final[tuple[str, ...]] = (
    "dune_4931834_downloaded",
    "dune_4931834_schema_validated",
    "dune_4931834_row_count_reconciled",
    "dex_trades_reconstructed",
    "dex_aggregator_trades_reconciled",
    "mempool_public_visibility_reconstructed",
    "atomic_mev_exclusions_reproduced",
    "ofa_backrun_exclusions_reproduced",
    "router_and_bot_exclusions_reproduced",
    "uniswap_x_filler_exclusions_reproduced",
    "287_token_universe_reproduced",
    "tardis_symbol_availability_verified",
    "tardis_quote_history_downloaded",
    "tardis_markout_grid_reproduced",
    "searcher_t_star_reestimated",
    "mevboost_payloads_downloaded",
    "ultrasound_adjustments_downloaded",
    "appendix_h_reconciled",
    "paper_headline_results_reconciled",
)


EXTENSION_DATASETS: Final[tuple[str, ...]] = (
    "tardis_binance_l2",
    "dex_pool_state_and_liquidity_curves",
    "multi_venue_cex_execution",
    "execution_probability",
    "hedge_latency",
    "uncertainty_intervals",
    "counterfactual_scenarios",
)
