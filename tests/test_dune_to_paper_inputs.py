import json

import pytest

from grandmotherbot_extension.dune_to_paper_inputs import build_paper_inputs, identify_rows


def row(**overrides):
    base = {
        "tx_hash": "0x1",
        "block_number": 18000000,
        "slot_time": "2024-01-01T00:00:00Z",
        "from_address": "0x1111111111111111111111111111111111111111",
        "observed_public_mempool": True,
        "first_swap_in_pool_direction": True,
        "atomic_mev": False,
        "liquidation": False,
        "ofa_backrun": False,
        "known_router": False,
        "labeled_trading_bot": False,
        "ens_named_eoa_controller": False,
        "erc721_transfer": False,
        "final_pair_major_cex_listed": True,
        "searcher_label": None,
        "builder": None,
        "log_index": 1,
        "dex": "uniswap",
        "pool": "0xpool",
        "token_in": "0xtokena",
        "token_out": "0xtokenb",
        "amount_in": 10,
        "amount_out": 9,
    }
    base.update(overrides)
    return base


def test_h1_h6_and_swaps_are_applied_without_guessing(tmp_path):
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps({"rows": [row()]}))
    result = build_paper_inputs(raw, tmp_path / "input")
    assert result == {"source_rows": 1, "transactions": 1, "swaps": 1, "excluded": 0}


def test_failed_heuristic_is_excluded(tmp_path):
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps({"rows": [row(known_router=True)]}))
    tx, excluded = identify_rows([row(known_router=True)])
    assert tx.empty
    assert excluded[0]["reason"] == "paper_heuristic_or_manual_exclusion"


def test_missing_identification_evidence_is_rejected():
    bad = row()
    del bad["observed_public_mempool"]
    with pytest.raises(ValueError, match="observed_public_mempool"):
        identify_rows([bad])
