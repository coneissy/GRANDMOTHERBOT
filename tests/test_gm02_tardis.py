from datetime import datetime, timezone
from decimal import Decimal

from grandmotherbot_paper.gm02 import (
    BboPoint,
    OrderBookState,
    bbo_from_book_ticker,
    markout_return,
    reconstruct_bbo_from_l2,
    select_bbo,
    simulate_fill,
    simulate_pair_hedge,
)
from grandmotherbot_paper.tardis import (
    RawTardisEvent,
    build_binance_filters,
    datetime_to_us,
    normalize_binance_event,
)


def test_binance_filters_are_lowercase_and_chunked():
    filters = build_binance_filters(
        ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        ["trade", "bookTicker"],
        max_symbols_per_filter=2,
    )
    assert [(f.channel, f.symbols) for f in filters] == [
        ("trade", ("btcusdt", "ethusdt")),
        ("trade", ("solusdt",)),
        ("bookTicker", ("btcusdt", "ethusdt")),
        ("bookTicker", ("solusdt",)),
    ]


def test_normalize_trade_uses_trade_timestamp_and_aggressor_side():
    now = datetime(2024, 1, 1, tzinfo=timezone.utc)
    raw = RawTardisEvent(
        exchange="binance",
        local_timestamp_us=datetime_to_us(now),
        connected=True,
        request_date="2024-01-01",
        minute_offset=0,
        message={
            "stream": "btcusdt@trade",
            "data": {
                "e": "trade",
                "E": 1704067200123,
                "s": "BTCUSDT",
                "t": 123,
                "p": "42000.5",
                "q": "0.01",
                "T": 1704067200111,
                "m": True,
            },
        },
    )
    event = normalize_binance_event(raw, 7)
    assert event is not None
    assert event.channel == "trade"
    assert event.exchange_timestamp_us == 1704067200111 * 1000
    assert event.side == "sell"
    assert event.trade_id == "123"
    assert event.price == "42000.5"


def test_book_ticker_uses_local_timestamp_because_binance_native_bbo_has_no_event_time():
    raw = RawTardisEvent(
        exchange="binance",
        local_timestamp_us=1704067200002131,
        connected=True,
        request_date="2024-01-01",
        minute_offset=0,
        message={
            "stream": "btcusdt@bookTicker",
            "data": {
                "u": 400900217,
                "s": "BTCUSDT",
                "b": "42283.58",
                "B": "9.07348",
                "a": "42283.59",
                "A": "2.79269",
            },
        },
    )
    event = normalize_binance_event(raw, 0)
    assert event is not None
    assert event.channel == "bookTicker"
    assert event.exchange_timestamp_us is None
    assert event.local_timestamp_us == 1704067200002131

    points = bbo_from_book_ticker([event])
    assert points[0].mid == Decimal("42283.585")
    assert points[0].spread_bps is not None


def test_depth_snapshot_and_diff_reconstruct_bbo():
    snapshot = RawTardisEvent(
        exchange="binance",
        local_timestamp_us=1000,
        connected=True,
        request_date="2024-01-01",
        minute_offset=0,
        message={
            "stream": "btcusdt@depthSnapshot",
            "generated": True,
            "data": {
                "lastUpdateId": 100,
                "bids": [["99", "3"], ["98", "10"]],
                "asks": [["101", "4"], ["102", "10"]],
            },
        },
    )
    diff = RawTardisEvent(
        exchange="binance",
        local_timestamp_us=2000,
        connected=True,
        request_date="2024-01-01",
        minute_offset=0,
        message={
            "stream": "btcusdt@depth@100ms",
            "data": {
                "e": "depthUpdate",
                "E": 1704067200002,
                "s": "BTCUSDT",
                "U": 101,
                "u": 101,
                "b": [["100", "5"]],
                "a": [["101", "0"], ["100.5", "2"]],
            },
        },
    )

    snapshot_event = normalize_binance_event(snapshot, 0)
    diff_event = normalize_binance_event(diff, 1)
    assert snapshot_event is not None
    assert diff_event is not None

    points = reconstruct_bbo_from_l2([snapshot_event, diff_event])
    assert points[-1].bid == Decimal("100")
    assert points[-1].ask == Decimal("100.5")
    assert points[-1].bid_amount == Decimal("5")
    assert points[-1].ask_amount == Decimal("2")


def test_order_book_gap_invalidates_until_next_snapshot():
    book = OrderBookState(bids={}, asks={})
    book.apply_snapshot([("99", "1")], [("101", "1")], 100)

    assert not book.apply_depth(103, 103, (), ())
    assert not book.valid
    assert not book.apply_depth(104, 104, (("100", "1"),), ())

    book.apply_snapshot([("99", "1")], [("101", "1")], 200)
    assert book.valid


def test_select_and_markout():
    points = [
        BboPoint(1_000_000, Decimal("99"), Decimal("10"), Decimal("101"), Decimal("10"), "bookTicker", 0),
        BboPoint(2_000_000, Decimal("100"), Decimal("10"), Decimal("102"), Decimal("10"), "bookTicker", 0),
        BboPoint(3_000_000, Decimal("103"), Decimal("10"), Decimal("105"), Decimal("10"), "bookTicker", 0),
    ]
    reference = select_bbo(points, 1_500_000, policy="last_at_or_before")
    target = select_bbo(points, 2_500_000, policy="first_at_or_after")

    assert reference is not None
    assert target is not None
    assert reference.mid == Decimal("100")
    assert target.mid == Decimal("104")
    assert markout_return(reference, target, direction="long") == Decimal("0.04")


def test_simulate_buy_and_sell_fills():
    buy_book = OrderBookState(
        bids={Decimal("99"): Decimal("10")},
        asks={Decimal("101"): Decimal("2"), Decimal("102"): Decimal("3")},
    )
    buy = simulate_fill(
        buy_book,
        side="buy",
        amount=Decimal("4"),
        max_levels=25,
    )
    assert buy.complete
    assert buy.vwap == Decimal("101.5")
    assert buy.notional == Decimal("406")

    sell_book = OrderBookState(
        bids={Decimal("101"): Decimal("2"), Decimal("100"): Decimal("3")},
        asks={Decimal("102"): Decimal("1")},
    )
    sell = simulate_fill(
        sell_book,
        side="sell",
        amount=Decimal("4"),
        max_levels=25,
    )
    assert sell.complete
    assert sell.vwap == Decimal("100.5")
    assert sell.notional == Decimal("402")


def test_pair_hedge_applies_fee_to_both_legs():
    book_a = OrderBookState(
        bids={Decimal("100"): Decimal("10")},
        asks={Decimal("101"): Decimal("10")},
    )
    book_b = OrderBookState(
        bids={Decimal("2"): Decimal("100")},
        asks={Decimal("2.1"): Decimal("100")},
    )
    result = simulate_pair_hedge(
        symbol_a_book=book_a,
        amount_a=Decimal("1"),
        symbol_b_book=book_b,
        amount_b=Decimal("10"),
        cex_fee_rate=Decimal("0.001"),
    )
    assert result.complete
    assert result.gross_proceeds_usd == Decimal("100")
    assert result.gross_cost_usd == Decimal("21")
    assert result.cex_fee_usd == Decimal("0.121")
    assert result.net_hedge_value_usd == Decimal("78.879")
