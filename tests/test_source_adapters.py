from datetime import datetime, timezone

import pytest

from grandmotherbot_extension.source_adapters import (
    DuneAdapter,
    MissingCredential,
    TardisAdapter,
    dune_rows,
    normalize_binance_book_ticker,
    parse_tardis_events,
    utc_iso,
)


def test_dune_query_is_locked_to_research_query():
    assert DuneAdapter().config.query_id == 4_931_834


def test_dune_rows_preserve_result_columns():
    result = {"result": {"rows": [{"tx_hash": "0x1", "amount": "1.25"}]}}
    assert dune_rows(result) == [{"tx_hash": "0x1", "amount": "1.25"}]


def test_credentials_are_required_before_network_access(monkeypatch):
    monkeypatch.delenv("DUNE_API_KEY", raising=False)
    with pytest.raises(MissingCredential):
        DuneAdapter().latest_result()

    monkeypatch.delenv("TARDIS_API_KEY", raising=False)
    with pytest.raises(MissingCredential):
        TardisAdapter().fetch_minute(from_iso="2025-01-01T00:00:00Z")


def test_tardis_events_remain_raw_and_disconnects_are_preserved():
    events = [
        {"capture_time": "2025-01-01T00:00:00Z", "message": {"e": "trade"}},
        {"disconnect": True},
    ]
    frame = parse_tardis_events(events)
    assert list(frame.columns) == ["capture_time", "message", "disconnect"]
    assert frame.iloc[0]["message"]["e"] == "trade"
    assert bool(frame.iloc[1]["disconnect"])


def test_binance_book_ticker_uses_native_fields():
    events = [
        {
            "capture_time": "2025-01-01T00:00:00.100Z",
            "message": {
                "e": "bookTicker",
                "u": 123,
                "s": "ETHUSDT",
                "b": "3000.10",
                "B": "1.2",
                "a": "3000.20",
                "A": "0.8",
                "E": 1735689600100,
            },
        }
    ]
    frame = normalize_binance_book_ticker(events)
    assert frame.iloc[0]["symbol"] == "ETHUSDT"
    assert frame.iloc[0]["event_time_ms"] == 1735689600100
    assert frame.iloc[0]["bid_price"] == "3000.10"
    assert frame.iloc[0]["ask_qty"] == "0.8"
    assert frame.iloc[0]["update_id"] == 123
    assert frame.iloc[0]["source"] == "tardis"


def test_utc_iso():
    assert utc_iso(datetime(2025, 1, 1, tzinfo=timezone.utc)) == "2025-01-01T00:00:00Z"
