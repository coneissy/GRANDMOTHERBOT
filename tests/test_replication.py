from decimal import Decimal
from datetime import datetime, timezone

import pandas as pd

from grandmotherbot_paper.builder import (
    aggregated_profit,
    aggregated_profit_margin,
    builder_profit_usd,
    builder_profit_eth,
    builder_profit_from_eth_usd,
    eth_to_usd,
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
    assert builder_profit_eth(Decimal("10"), Decimal("4"), True, Decimal("2"), after) == Decimal("7")
    assert eth_to_usd(Decimal("2"), Decimal("3000")) == Decimal("6000")
    assert builder_profit_from_eth_usd(
        Decimal("10"), Decimal("4"), True, Decimal("2"), Decimal("3000"), after
    ) == Decimal("21000")
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


def test_top_level_reproduction_uses_dynamic_tardis_path(tmp_path):
    from grandmotherbot_paper.cex_mapping import BinanceToken
    from grandmotherbot_paper.dynamic_pipeline import DynamicPipelineConfig
    from grandmotherbot_paper.reproduction import build_paper_markouts

    day = tmp_path / "2024-01-01"
    day.mkdir()
    base = 1704067200000000
    rows = []
    for i in range(25):
        ts = base - 1_000_000 + i * 500_000
        for symbol, ask, bid in (("AAA", "101", "99"), ("BBB", "2", "1")):
            rows.append({
                "exchange": "binance", "symbol": symbol, "timestamp": ts,
                "local_timestamp": ts, "ask_amount": "100", "ask_price": ask,
                "bid_price": bid, "bid_amount": "100",
            })
    frame = pd.DataFrame(rows)
    for symbol in ("AAA", "BBB"):
        frame[frame.symbol == symbol].to_csv(
            day / f"{symbol}.csv.gz", index=False, compression="gzip"
        )

    transactions = pd.DataFrame([{
        "tx_hash": "0x1", "block_number": 1,
        "slot_time": "2024-01-01T00:00:00Z", "searcher_label": "Test",
        "volume_usd": "1000",
        "observed_public_mempool": False, "first_swap_in_pool_direction": True,
        "atomic_mev": False, "liquidation": False, "ofa_backrun": False,
        "known_router": False, "labeled_trading_bot": False,
        "ens_named_eoa_controller": False, "erc721_transfer": False,
        "final_pair_major_cex_listed": True, "from_address": "0xabc",
    }])
    swaps = pd.DataFrame([{
        "tx_hash": "0x1", "log_index": 0,
        "token_in": "0x0000000000000000000000000000000000000001",
        "token_out": "0x0000000000000000000000000000000000000002",
        "amount_in": "10", "amount_out": "20",
    }])
    tokens = [
        BinanceToken("AAA", "0x0000000000000000000000000000000000000001"),
        BinanceToken("BBB", "0x0000000000000000000000000000000000000002"),
    ]

    out = build_paper_markouts(
        transactions, swaps, tokens, DynamicPipelineConfig(tmp_path)
    )
    assert len(out) == 23
    assert set(out.horizon_s) == {str(-1.0 + i * 0.5) for i in range(23)}


def test_aligned_economics_keeps_negative_ev_for_pnl_but_null_margin():
    from grandmotherbot_paper.aligned import score_aligned

    markouts = pd.DataFrame([{
        "tx_hash": "0x1", "searcher_label": "Test", "horizon_s": "1.0",
        "amount_a": "1", "amount_b": "100", "token_a_usdt_mid": "100",
        "token_b_usdt_mid": "1", "cex_taker_fees_usd": "1",
        "dex_volume_usd": "100", "base_fees_usd": "10", "builder_tips_usd": "5",
    }])
    tstars = pd.DataFrame([{"searcher_label": "Test", "computed_t_star_s": Decimal("1.0")}])
    out = score_aligned(markouts, tstars)
    assert len(out) == 1
    assert out.iloc[0].ev_usd == Decimal("-11")
    assert out.iloc[0].pnl_usd == Decimal("-16")
    assert pd.isna(out.iloc[0].profit_margin)


def test_aligned_economics_uses_computed_tstar_not_published_tstar():
    from grandmotherbot_paper.aligned import score_aligned

    markouts = pd.DataFrame([
        {
            "tx_hash": "0x1", "searcher_label": "Wintermute", "horizon_s": h,
            "amount_a": "1", "amount_b": "1", "token_a_usdt_mid": "110",
            "token_b_usdt_mid": "100", "cex_taker_fees_usd": "1",
            "dex_volume_usd": "100", "base_fees_usd": "1", "builder_tips_usd": "1",
        }
        for h in ("0.5", "1.5")
    ])
    tstars = pd.DataFrame([{"searcher_label": "Wintermute", "computed_t_star_s": Decimal("0.5")}])
    out = score_aligned(markouts, tstars)
    assert out.iloc[0].t_star_s == Decimal("0.5")
