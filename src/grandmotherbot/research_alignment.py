from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final


PAPER_ID: Final = "arXiv:2507.13023 / LIPIcs.AFT.2025.26"
SAMPLE_START: Final = datetime(2023, 8, 8)
SAMPLE_END: Final = datetime(2025, 3, 8)

# Primary reproducibility target identified in the published paper.
DUNE_QUERY_ID: Final = 4931834
DUNE_QUERY_URL: Final = "https://dune.com/queries/4931834"
DUNE_DASHBOARD_URL: Final = "https://dune.com/rig_ef/cex-dex-dash"

# Appendix-H reconciliation targets. These are targets from the paper, not
# locally observed row counts until the corresponding raw data are ingested.
CURATED_TRANSACTIONS: Final = 8_723_233
MISSING_TARDIS_PRICES: Final = 163_148
INVENTORY_ADJUSTMENTS: Final = 683_539
IDENTIFIED_ARBITRAGES: Final = 7_203_560
IDENTIFIED_VOLUME_USD: Final = 241_700_000
EXTRACTED_VALUE_USD: Final = 233_800_000


@dataclass(frozen=True)
class ResearchSource:
    name: str
    kind: str
    location: str
    required_for: tuple[str, ...]


SOURCES: Final = (
    ResearchSource(
        "Dune CEX-DEX transactions",
        "historical",
        DUNE_QUERY_URL,
        ("identification", "appendix_h_reconciliation", "searcher_landscape"),
    ),
    ResearchSource(
        "Dune CEX-DEX dashboard",
        "historical",
        DUNE_DASHBOARD_URL,
        ("paper_replication", "visual_validation"),
    ),
    ResearchSource(
        "Binance Spot / Tardis",
        "historical_market_data",
        "https://api.tardis.dev/v1/exchanges/binance",
        ("markout", "hedge_latency", "order_book_reconstruction"),
    ),
    ResearchSource(
        "MEV-Boost / RelayScan",
        "historical_builder_data",
        "https://www.relayscan.io/",
        ("builder_attribution", "execution_path", "builder_economics"),
    ),
    ResearchSource(
        "Ultra Sound relay adjustments",
        "historical_builder_adjustments",
        "https://relay.ultrasound.money/ultrasound/v1/data/adjustments",
        ("appendix_g", "builder_economics"),
    ),
)


# The paper's identification layer is deliberately separated from the
# empirical extensions. This prevents an estimated markout from being
# mistaken for an observed CEX hedge.
EMPIRICAL_LAYERS: Final = {
    "identification": ("dune_cex_dex",),
    "cex_prices": ("tardis_binance",),
    "cex_order_book": ("tardis_binance",),
    "builder_bids": ("mev_boost_relayscan",),
    "ultra_sound_adjustments": ("ultra_sound",),
    "execution_probability": (
        "dune_cex_dex",
        "mev_boost_relayscan",
        "block_timing",
    ),
    "hedge_latency": ("dune_cex_dex", "tardis_binance"),
    "uncertainty": (
        "tardis_binance",
        "dune_cex_dex",
        "mev_boost_relayscan",
    ),
    "counterfactuals": (
        "dune_cex_dex",
        "tardis_binance",
        "mev_boost_relayscan",
        "ultra_sound",
    ),
}
