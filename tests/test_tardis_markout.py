from datetime import date
from decimal import Decimal

import pandas as pd

from grandmotherbot_paper.tardis import (
    PAPER_CEX_FEE_RATE,
    asof_quote,
    cex_taker_fee,
    daily_quotes_url,
    markout_horizons_s,
    markout_targets,
    read_quotes_frame,
)


def _frame():
    return pd.DataFrame(
        [
            {
                "exchange": "binance",
                "symbol": "WETHUSDT",
                "timestamp": 1_000_000,
                "local_timestamp": 1_000_100,
                "ask_amount": "10",
                "ask_price": "2001",
                "bid_price": "1999",
                "bid_amount": "10",
            },
            {
                "exchange": "binance",
                "symbol": "WETHUSDT",
                "timestamp": 1_500_000,
                "local_timestamp": 1_500_100,
                "ask_amount": "10",
                "ask_price": "2003",
                "bid_price": "2001",
                "bid_amount": "10",
            },
        ]
    )


def test_tardis_quote_schema_and_midpoint():
    quotes = read_quotes_frame(_frame(), symbol="WETHUSDT")
    assert quotes[0].mid_price == Decimal("2000")
    assert quotes[0].timestamp_us == 1_000_000


def test_asof_uses_last_quote_at_or_before_markout_timestamp():
    quotes = read_quotes_frame(_frame(), symbol="WETHUSDT")
    match = asof_quote(quotes, 1_499_999)
    assert match is not None
    assert match.quote.timestamp_us == 1_000_000
    assert match.staleness_us == 499_999


def test_future_quote_is_never_used():
    quotes = read_quotes_frame(_frame(), symbol="WETHUSDT")
    assert asof_quote(quotes, 999_999) is None


def test_horizons_are_23_points():
    horizons = markout_horizons_s()
    assert len(horizons) == 23
    assert horizons[0] == Decimal("-1.0")
    assert horizons[-1] == Decimal("10.0")


def test_targets_are_500ms_spaced():
    targets = markout_targets(10_000_000)
    assert len(targets) == 23
    assert targets[0] == 9_000_000
    assert targets[-1] == 20_000_000
    assert all(b - a == 500_000 for a, b in zip(targets, targets[1:]))


def test_paper_fee_is_locked():
    assert PAPER_CEX_FEE_RATE == Decimal("0.0001725")
    assert cex_taker_fee(Decimal("10000")) == Decimal("1.725")


def test_daily_url():
    assert daily_quotes_url(date(2024, 1, 1), "ethusdt").endswith(
        "/2024/01/01/ETHUSDT.csv.gz"
    )
