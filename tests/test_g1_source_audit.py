from grandmotherbot_extension.g1_audit import audit_rows

def test_audit_rows_basic():
    rows = [{"tx_hash": "0x1", "block_number": 18000000, "block_time": "2024-01-01T00:00:00Z"}]
    report = audit_rows(rows)
    assert report["source_rows"] == 1
    assert report["unique_tx_hashes"] == 1
    assert report["in_paper_block_range"] == 1
    assert report["in_paper_date_range"] == 1
