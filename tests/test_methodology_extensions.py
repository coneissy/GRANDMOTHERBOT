from datetime import datetime, timezone

import pytest

from grandmotherbot.methodology_extensions import (
    AuctionObservation,
    BlockInterval,
    CexExecution,
    PriceRegime,
    executable_pnl,
    lvr_diagnostic,
)


def test_block_interval_is_empirical_and_monotone():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = datetime(2026, 1, 1, 0, 0, 12, tzinfo=timezone.utc)
    assert BlockInterval(start, end).seconds == 12


def test_jump_regime_is_separate_from_diffusive_regime():
    assert PriceRegime(101.0, 100.0, jump_bps_threshold=50).classify() == "jump"
    assert PriceRegime(100.1, 100.0, jump_bps_threshold=50).classify() == "diffusive"


def test_executable_pnl_deducts_measured_execution_friction():
    execution = CexExecution("sell", 10, 99, 100, fees_usd=2, slippage_usd=3)
    assert executable_pnl(100, execution, extra_latency_cost_usd=1) == 94


def test_lvr_is_only_a_diagnostic():
    assert lvr_diagnostic(101, 100, 10) == 10


def test_auction_observation_validates():
    AuctionObservation(1, "builder", 100, True).validate()


def test_invalid_execution_rejected():
    with pytest.raises(ValueError):
        CexExecution("sell", 0, 99, 100).notional_usd
