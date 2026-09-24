from decimal import Decimal

from grandmother.builder import is_block_subsidized
from grandmother.economics import TradeEconomics
from grandmother.heuristics import passes_heuristics, heuristic_report
from grandmother.markout import HORIZONS, optimal_horizon
from grandmother.models import CandidateTransaction, HedgeObservation, MarkoutPoint, PoolSwap
from grandmother.reconstruction import reconstruct_effective_trade


def candidate(**overrides):
    base = dict(
        tx_hash="0x1",
        block_number=1,
        slot_time_ms=0,
        searcher=None,
        swaps=(
            PoolSwap("p1", "dex", "A", "B", Decimal("10"), Decimal("20")),
        ),
        observed_in_public_mempool=False,
        first_swap_in_pool_direction=True,
        is_atomic_mev=False,
        is_liquidation=False,
        is_ofa_backrun=False,
        is_known_router=False,
        is_labeled_trading_bot=False,
        controls_ens_named_eoa=False,
        contains_erc721_transfer=False,
        final_tokens_cex_listed=True,
    )
    base.update(overrides)
    return CandidateTransaction(**base)


def test_six_heuristics_gate():
    assert passes_heuristics(candidate())
    assert not passes_heuristics(candidate(observed_in_public_mempool=True))
    assert not passes_heuristics(candidate(is_atomic_mev=True))
    report = heuristic_report(candidate(is_ofa_backrun=True))
    assert report["H4_not_ofa_backrun"] is False


def test_multi_swap_reconstruction():
    swaps = (
        PoolSwap("p1", "dex", "A", "B", Decimal("10"), Decimal("20")),
        PoolSwap("p2", "dex", "B", "C", Decimal("20"), Decimal("30")),
    )
    result = reconstruct_effective_trade(swaps, {"A": Decimal("2"), "C": Decimal("5")})
    assert result.token_a == "C"
    assert result.token_b == "A"
    assert result.amount_a == Decimal("30")
    assert result.amount_b == Decimal("10")
    assert result.volume_token_a_usd == Decimal("150")


def make_obs(offsets):
    points = tuple(
        MarkoutPoint(
            Decimal("-1.0") + Decimal("0.5") * i,
            Decimal("100") + offsets[i],
            Decimal("1"),
        )
        for i in range(23)
    )
    return HedgeObservation("A", "B", Decimal("1"), Decimal("99"), Decimal("100"), Decimal("0"), points)


def test_markout_has_exact_research_horizons():
    assert HORIZONS[0] == Decimal("-1.0")
    assert HORIZONS[-1] == Decimal("10.0")
    assert len(HORIZONS) == 23


def test_t_star_chooses_largest_tie():
    offsets = [Decimal("0") for _ in range(23)]
    offsets[10] = Decimal("5")
    offsets[11] = Decimal("5")
    obs = make_obs(offsets)
    assert optimal_horizon([obs]) == Decimal("4.0")


def test_ev_pnl_margin_and_negative_ev_margin():
    e = TradeEconomics(Decimal("100"), Decimal("20"), Decimal("10"))
    assert e.estimated_ev_usd == Decimal("80")
    assert e.estimated_pnl_usd == Decimal("70")
    assert e.profit_margin == Decimal("0.875")
    losing = TradeEconomics(Decimal("10"), Decimal("20"), Decimal("10"))
    assert losing.estimated_ev_usd == Decimal("-10")
    assert losing.profit_margin is None


def test_subsidy_definition():
    assert is_block_subsidized(Decimal("-1"), Decimal("-1"))
    assert not is_block_subsidized(Decimal("1"), Decimal("-100"))
