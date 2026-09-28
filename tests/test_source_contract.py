from grandmotherbot_paper.constants import HORIZONS
from grandmotherbot_paper.source_contract import input_readiness, paper_contract

def test_source_contract_keeps_paper_horizon_grid():
    contract = paper_contract()
    assert contract["paper_period"]["start_block"] == 17866488
    assert contract["paper_period"]["end_block"] == 21998438
    assert len(contract["markout_horizons_s"]) == len(HORIZONS) == 23
    assert contract["markout_horizons_s"][0] == "-1.0"
    assert contract["markout_horizons_s"][-1] == "10.0"

def test_input_readiness_does_not_invent_missing_data(tmp_path):
    status = input_readiness(tmp_path)
    assert status["ready"] is False
    assert all(item["present"] is False for item in status["files"].values())
