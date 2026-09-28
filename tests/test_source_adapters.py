import os

import pytest

from grandmotherbot_extension.source_adapters import (
    DuneAdapter,
    MissingCredential,
    TardisAdapter,
    parse_tardis_events,
    utc_iso,
)


def test_dune_query_is_locked_to_research_query():
    assert DuneAdapter().config.query_id == 4_931_834


def test_credentials_are_required_before_network_access(monkeypatch):
    monkeypatch.delenv("DUNE_API_KEY", raising=False)
    with pytest.raises(MissingCredential):
        DuneAdapter().latest_result()

    monkeypatch.delenv("TARDIS_API_KEY", raising=False)
    with pytest.raises(MissingCredential):
        TardisAdapter().fetch_minute(from_iso="2025-01-01T00:00:00Z")


def test_tardis_events_remain_raw():
    events = [{"capture_time": "2025-01-01T00:00:00Z", "message": {"table": "trade"}}]
    frame = parse_tardis_events(events)
    assert list(frame.columns) == ["capture_time", "message"]
    assert frame.iloc[0]["message"]["table"] == "trade"


def test_utc_iso():
    from datetime import datetime, timezone
    assert utc_iso(datetime(2025, 1, 1, tzinfo=timezone.utc)) == "2025-01-01T00:00:00Z"
