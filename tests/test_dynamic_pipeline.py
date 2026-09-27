from decimal import Decimal
from pathlib import Path

import pandas as pd

from grandmotherbot_paper.cex_mapping import BinanceToken
from grandmotherbot_paper.dynamic_pipeline import DynamicPipelineConfig, build_markout_inputs, build_dynamic_markouts


def _h1_h6_fields():
    return {
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
        "from_address": "0xabc",
    }


def test_build_markout_inputs_reconstructs_and_maps_contracts():
    tx_row = {
        "tx_hash": "0x1", "block_number": 1, "slot_time": "2024-01-01T00:00:00Z",
        "searcher_label": "Test", "volume_usd": "1000", **_h1_h6_fields(),
    }
    tx = pd.DataFrame([tx_row])
    swaps = pd.DataFrame([{
        "tx_hash":"0x1","log_index":0,
        "token_in":"0x0000000000000000000000000000000000000001",
        "token_out":"0x0000000000000000000000000000000000000002",
        "amount_in":"10","amount_out":"20",
    }])
    tokens = [
        BinanceToken("AAA", "0x0000000000000000000000000000000000000001"),
        BinanceToken("BBB", "0x0000000000000000000000000000000000000002"),
    ]
    out = build_markout_inputs(tx, swaps, tokens)
    assert len(out) == 1
    assert out.iloc[0].bought_symbol == "BBB"
    assert out.iloc[0].sold_symbol == "AAA"
    assert out.iloc[0].amount_bought == "20"


def test_dynamic_markouts_consume_cached_quote_files(tmp_path: Path):
    day = tmp_path / "2024-01-01"
    day.mkdir()
    base = 1704067200000000
    rows = []
    for i in range(25):
        ts = base - 1_000_000 + i * 500_000
        rows.append({
            "exchange":"binance","symbol":"AAA","timestamp":ts,"local_timestamp":ts,
            "ask_amount":"100","ask_price":"101","bid_price":"99","bid_amount":"100",
        })
        rows.append({
            "exchange":"binance","symbol":"BBB","timestamp":ts,"local_timestamp":ts,
            "ask_amount":"100","ask_price":"2","bid_price":"1","bid_amount":"100",
        })
    frame = pd.DataFrame(rows)
    frame[frame.symbol == "AAA"].to_csv(day / "AAA.csv.gz", index=False, compression="gzip")
    frame[frame.symbol == "BBB"].to_csv(day / "BBB.csv.gz", index=False, compression="gzip")

    inputs = pd.DataFrame([{
        "tx_hash":"0x1","block_number":1,"slot_time":"2024-01-01T00:00:00Z",
        "searcher_label":"Test","amount_bought":"20","amount_sold":"10",
        "dex_volume_usd":"1000","bought_symbol":"BBB","sold_symbol":"AAA",
    }])
    out = build_dynamic_markouts(inputs, DynamicPipelineConfig(tmp_path))
    assert len(out) == 23
    assert set(out.horizon_s) == {str(-1.0 + i * 0.5) for i in range(23)}
    assert all(Decimal(str(v)) == Decimal("0.345") for v in out.cex_taker_fees_usd)


def test_dynamic_pipeline_excludes_incomplete_tardis_window(tmp_path: Path):
    day = tmp_path / "2024-01-01"
    day.mkdir()
    base = 1704067200000000
    frame = pd.DataFrame([{
        "exchange":"binance","symbol":"AAA","timestamp":base,"local_timestamp":base,
        "ask_amount":"100","ask_price":"101","bid_price":"99","bid_amount":"100",
    }])
    frame.to_csv(day / "AAA.csv.gz", index=False, compression="gzip")
    frame.to_csv(day / "BBB.csv.gz", index=False, compression="gzip")
    inputs = pd.DataFrame([{
        "tx_hash":"0x1","block_number":1,"slot_time":"2024-01-01T00:00:00Z",
        "searcher_label":"Test","amount_bought":"20","amount_sold":"10",
        "dex_volume_usd":"1000","bought_symbol":"BBB","sold_symbol":"AAA",
    }])
    out = build_dynamic_markouts(inputs, DynamicPipelineConfig(tmp_path))
    assert out.empty
