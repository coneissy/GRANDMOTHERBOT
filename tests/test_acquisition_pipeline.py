import json

from grandmotherbot_extension.acquisition_pipeline import (
    acquisition_summary,
    acquire_dune_query,
    acquire_tardis_minutes,
)


def test_dune_acquisition_writes_raw_only(monkeypatch, tmp_path):
    class FakeAdapter:
        def run(self, max_age_hours=None):
            return {"result": {"rows": [{"tx_hash": "0x1"}], "metadata": {"ok": True}}}

    monkeypatch.setattr(
        "grandmotherbot_extension.acquisition_pipeline.DuneAdapter",
        lambda: FakeAdapter(),
    )

    result = acquire_dune_query(output=tmp_path / "dune.json")
    assert result.rows_received == 1
    assert (tmp_path / "dune.json").is_file()
    assert (tmp_path / "dune.manifest.json").is_file()
    assert not list(tmp_path.glob("data/input/*.csv"))


def test_tardis_window_is_minute_resumable(monkeypatch, tmp_path):
    class FakeAdapter:
        def fetch_minute(self, **kwargs):
            return [
                {"capture_time": "2025-01-01T00:00:00Z", "message": {"e": "bookTicker"}},
                {"disconnect": True},
            ]

    monkeypatch.setattr(
        "grandmotherbot_extension.acquisition_pipeline.TardisAdapter",
        lambda: FakeAdapter(),
    )

    results = acquire_tardis_minutes(
        start_iso="2025-01-01T00:00:00Z",
        minutes=2,
        output_dir=tmp_path,
    )
    assert len(results) == 2
    assert all(item.rows_received == 2 for item in results)
    assert (tmp_path / "minute_000000.ndjson").is_file()
    assert (tmp_path / "minute_000001.ndjson").is_file()

    lines = (tmp_path / "minute_000000.ndjson").read_text().splitlines()
    assert json.loads(lines[1])["disconnect"] is True


def test_acquisition_summary():
    class R:
        def __init__(self, n):
            self.source = "x"
            self.output = f"f{n}"
            self.rows_received = n
            self.retrieved_at = "2025-01-01T00:00:00Z"

    summary = acquisition_summary([R(2), R(3)])
    assert summary["total_rows_received"] == 5
    assert len(summary["results"]) == 2
