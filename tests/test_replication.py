from decimal import Decimal
from datetime import datetime, timezone

import pandas as pd

from grandmotherbot_paper.builder import (
    aggregated_profit,
    aggregated_profit_margin,
    builder_profit_usd,
    is_exclusive_searcher,
    is_subsidized_block,
)
from grandmotherbot_paper.constants import HORIZONS, KNOWN_PATTERN_BY_SEARCHER
from grandmotherbot_paper.identification import CandidateTransaction, passes_all_heuristics
from grandmotherbot_paper.liquidity import pair_class
from grandmotherbot_paper.markout import (
    MarkoutPoint,
    TradeObservation,
    inventory_adjustment_like_observation,
    optimal_horizon,
)
from grandmotherbot_paper.profitability import (
    estimated_ev,
    estimated_pnl,
    inventory_adjustment_like,
    profit_margin,
)
from grandmotherbot_paper.reproduction import build_observations
from grandmotherbot_paper.reconstruction import Swap, reconstruct_effective_trade


def test_exact_markout_grid():
    assert HORIZONS[0] == Decimal("-1.0")
    assert HORIZONS[-1] == Decimal("10.0")
    assert len(HORIZONS) == 23


def test_all_six_heuristics_are_strict():
    good = CandidateTransaction(False, True, False, False, False, False, False, False, False, True)
    assert passes_all_heuristics(good)
    assert not passes_all_heuristics(CandidateTransaction(True, True, False, False, False, False, False, False, False, True))
    assert not passes_all_heuristics(CandidateTransaction(False, True, True, False, False, False, False, False, False, True))
    assert not passes_all_heuristics(CandidateTransaction(False, True, False, False, True, False, False, False, False, True))
    assert not passes_all_heuristics(CandidateTransaction(False, True, False, False, False, True, False, False, False, True))
    assert not passes_all_heuristics(CandidateTransaction(False, True, False, False, False, False, False, False, False, False))


def test_appendix_f_manual_exclusion():
    tx = CandidateTransaction(False, True, False, False, False, False, False, False, False, True, "0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789")
    assert not passes_all_heuristics(tx)


def test_multi_swap_reconstruction():
    result = reconstruct_effective_trade((
        Swap("A", "B", Decimal("10"), Decimal("20"), 0),
        Swap("B", "C", Decimal("20"), Decimal("30"), 1),
    ))
    assert result.token_bought == "C"
    assert result.amount_bought == Decimal("30")
    assert result.token_sold == "A"
    assert result.amount_sold == Decimal("10")


def test_t_star_largest_tied_horizon():
    points = tuple(
        MarkoutPoint(h, Decimal("100") + Decimal(i), Decimal("1"))
        for i, h in enumerate(HORIZONS)
    )
    obs = TradeObservation(Decimal("1"), Decimal("99"), Decimal("100"), Decimal("0"), points)
    assert optimal_horizon([obs]) == Decimal("10.0")


def test_inventory_adjustment_is_excluded_from_markout_observation():
    points = tuple(
        MarkoutPoint(h, Decimal("100"), Decimal("1"))
        for h in HORIZONS
    )
    obs = TradeObservation(
        Decimal("1"),
        Decimal("99"),
        Decimal("100"),
        Decimal("0"),
        points,
        Decimal("1"),
    )
    assert inventory_adjustment_like_observation(obs)


def test_profitability_and_margin_rules():
    ev = estimated_ev(Decimal("100"), Decimal("20"))
    pnl = estimated_pnl(ev, Decimal("10"))
    assert ev == Decimal("80")
    assert pnl == Decimal("70")
    assert profit_margin(ev, pnl) == Decimal("0.875")
    assert profit_margin(Decimal("-1"), Decimal("-11")) is None
    assert inventory_adjustment_like([Decimal("0"), Decimal("0.9")], Decimal("1"))


def test_builder_profit_with_ultra_sound():
    before = datetime(2024, 1, 1, tzinfo=timezone.utc)
    after = datetime(2024, 4, 1, tzinfo=timezone.utc)
    assert builder_profit_usd(Decimal("10"), Decimal("4"), True, Decimal("2"), before) == Decimal("8")
    assert builder_profit_usd(Decimal("10"), Decimal("4"), True, Decimal("2"), after) == Decimal("7")
    assert aggregated_profit(Decimal("8"), Decimal("3")) == Decimal("11")
    assert aggregated_profit_margin(Decimal("11"), Decimal("4"), Decimal("2"), before, True) == Decimal("11") / (Decimal("11") + Decimal("4") - Decimal("2"))


def test_subsidy_and_exclusivity_rules():
    assert is_subsidized_block(Decimal("-1"), Decimal("-2"))
    assert not is_subsidized_block(Decimal("1"), Decimal("-2"))
    assert is_exclusive_searcher(Decimal("51"), Decimal("100"))
    assert not is_exclusive_searcher(Decimal("50"), Decimal("100"))


def test_liquidity_groups():
    assert pair_class("WETH", "USDC") == "Major-Major"
    assert pair_class("WETH", "ABC") == "Major-ALT"
    assert pair_class("ABC", "XYZ") == "ALT-ALT"


def test_published_pattern_metadata():
    assert KNOWN_PATTERN_BY_SEARCHER["Bard"] == (None, 3)
    assert KNOWN_PATTERN_BY_SEARCHER["Wintermute"] == (Decimal("1.5"), 1)
