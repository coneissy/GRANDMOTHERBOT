from grandmotherbot_extension.g3_population import build_g3_report


def row(tx_hash="0x1", **overrides):
    base = {
        "tx_hash": tx_hash,
        "block_number": 18000000,
        "slot_time": "2024-01-01T00:00:00Z",
        "from_address": "0x1111111111111111111111111111111111111111",
        "observed_public_mempool": False,
        "first_swap_in_pool_direction": True,
        "atomic_mev": False,
        "liquidation": False,
        "ofa_backrun": False,
        "known_router": False,
        "labeled_trading_bot": False,
        "ens_named_eoa_controller": False,
        "erc721_transfer": False,
        "final_pair_major_cex_listed": True,
    }
    base.update(overrides)
    return base


def test_g3_funnel_counts_each_heuristic():
    rows = [
        row("0x1"),
        row("0x2", known_router=True),
        row("0x3", observed_public_mempool=True),
    ]
    report = build_g3_report(rows)
    assert report.source_rows == 3
    assert report.unique_tx_hashes == 3
    assert report.duplicate_rows == 0
    assert report.in_block_range == 3
    assert report.in_date_range == 3
    assert report.funnel_counts["source_unique"] == 3
    assert report.funnel_counts["H1_private"] == 2
    assert report.funnel_counts["H2_first_swap_pool_direction"] == 2
    assert report.final_candidates == 1


def test_g3_deduplicates_by_transaction_hash():
    report = build_g3_report([row("0x1"), row("0x1"), row("0x2")])
    assert report.unique_tx_hashes == 2
    assert report.duplicate_rows == 1
    assert report.final_candidates == 2


def test_g3_respects_paper_block_and_date_bounds():
    report = build_g3_report([
        row("0x1", block_number=17866487),
        row("0x2", block_number=17866488),
        row("0x3", block_number=21998438),
        row("0x4", block_number=21998439),
    ])
    assert report.in_block_range == 2
    assert report.in_date_range == 2


def test_g3_reports_expected_delta_without_forcing_match():
    report = build_g3_report([row("0x1")], expected_candidate_population=8723233)
    assert report.final_candidates == 1
    assert report.expected_delta == 1 - 8723233
