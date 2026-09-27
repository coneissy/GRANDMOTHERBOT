from pathlib import Path

import pytest

from grandmotherbot import acquisition


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_download_dune_query_paginates_and_preserves_all_rows(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("DUNE_API_KEY", "test-key")
    calls = []

    def fake_get(url, *, headers, params, timeout):
        calls.append((url, headers, params, timeout))
        if params["offset"] == 0:
            return _Response({"result": {"rows": [{"tx_hash": "a"}, {"tx_hash": "b"}]}, "next_offset": 2})
        return _Response({"result": {"rows": [{"tx_hash": "c"}]}})

    monkeypatch.setattr(acquisition.requests, "get", fake_get)
    output = tmp_path / "dune.json"

    path = acquisition.download_dune_query(output=output, limit=2)

    assert path == output
    assert [call[2] for call in calls] == [
        {"limit": 2, "offset": 0},
        {"limit": 2, "offset": 2},
    ]
    payload = __import__("json").loads(output.read_text(encoding="utf-8"))
    assert payload["result"]["rows"] == [
        {"tx_hash": "a"}, {"tx_hash": "b"}, {"tx_hash": "c"}
    ]
    assert payload["pagination"] == {"page_size": 2, "pages": 2, "row_count": 3}


def test_download_dune_query_requires_positive_limit(monkeypatch):
    monkeypatch.setenv("DUNE_API_KEY", "test-key")
    with pytest.raises(ValueError, match="limit must be positive"):
        acquisition.download_dune_query(limit=0)
