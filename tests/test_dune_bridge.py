import pandas as pd
import pytest

from grandmotherbot_paper.dune_bridge import (
    normalize_dune_transactions,
    reconstruct_dune_transactions,
)
from grandmotherbot_paper.io import TRANSACTION_COLUMNS


def _tx(tx_hash="0x1"):
    row = {column: False for column in TRANSACTION_COLUMNS}
    row.update({
        "tx_hash": tx_hash,
        "block_number": 1,
        "slot_time": "2024-01-01T00:00:00Z",
        "from_address": "0xabc",
        "volume_usd": 100,
        "searcher_label": "searcher",
    })
    return row


def test_normalize_dune_transactions_preserves_canonical_columns():
    frame = normalize_dune_transactions([_tx()])
    assert list(frame.columns) == TRANSACTION_COLUMNS
    assert frame["tx_hash"].tolist() == ["0x1"]


def test_normalize_dune_transactions_rejects_duplicate_transactions():
    with pytest.raises(ValueError, match="duplicate tx_hash"):
        normalize_dune_transactions([_tx(), _tx()])


def test_dune_transactions_flow_into_effective_trade():
    transactions = pd.DataFrame([_tx()])
    swaps = pd.DataFrame([
        {"tx_hash": "0x1", "log_index": 0, "token_in": "A", "token_out": "B", "amount_in": "10", "amount_out": "20"},
        {"tx_hash": "0x1", "log_index": 1, "token_in": "B", "token_out": "C", "amount_in": "20", "amount_out": "30"},
    ])

    result = reconstruct_dune_transactions(transactions, swaps)

    assert len(result) == 1
    assert result.loc[0, "tx_hash"] == "0x1"
    assert result.loc[0, "token_sold_contract"] == "A"
    assert result.loc[0, "token_sold_amount"] == 10
    assert result.loc[0, "token_bought_contract"] == "C"
    assert result.loc[0, "token_bought_amount"] == 30


def test_reconstruction_rejects_swap_for_unknown_transaction():
    transactions = pd.DataFrame([_tx()])
    swaps = pd.DataFrame([{
        "tx_hash": "0x2", "log_index": 0, "token_in": "A", "token_out": "B",
        "amount_in": "1", "amount_out": "2",
    }])
    with pytest.raises(ValueError, match="unknown tx_hash"):
        reconstruct_dune_transactions(transactions, swaps)
