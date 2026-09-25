from datetime import datetime, timezone

from grandmotherbot_paper.cross_chain import (
    LayerZeroEvent,
    attach_cross_chain_features,
    bridge_activity_score,
    build_cross_chain_profiles,
    parse_dune_layerzero_rows,
)


def test_parse_layerzero_rows_normalizes_sender_and_time():
    rows = [{
        "sender": "0xABC",
        "call_block_time": "2024-01-01T12:00:00Z",
        "_srcChainId": 101,
        "_dstChainId": 110,
        "tx_hash": "0xTX",
    }]
    event = parse_dune_layerzero_rows(rows)[0]
    assert event.sender == "0xabc"
    assert event.call_block_time == datetime(
        2024, 1, 1, 12, 0, tzinfo=timezone.utc
    )
    assert event.cross_chain
    assert event.tx_hash == "0xtx"


def test_profiles_capture_chain_fingerprint():
    events = [
        LayerZeroEvent(
            "0xa", datetime(2024, 1, 1, tzinfo=timezone.utc), 101, 110
        ),
        LayerZeroEvent(
            "0xa", datetime(2024, 1, 2, tzinfo=timezone.utc), 101, 102
        ),
        LayerZeroEvent(
            "0xa", datetime(2024, 1, 3, tzinfo=timezone.utc), 110, 101
        ),
    ]
    profile = build_cross_chain_profiles(events)[0]
    assert profile.user_tx_count == 3
    assert profile.unique_source_chains == (101, 110)
    assert profile.unique_destination_chains == (101, 102, 110)
    assert profile.unique_chain_pairs == (
        (101, 102),
        (101, 110),
        (110, 101),
    )


def test_features_are_descriptive_not_arbitrage_labels():
    profile = build_cross_chain_profiles([
        LayerZeroEvent(
            "0xa", datetime(2024, 1, 1, tzinfo=timezone.utc), 101, 110
        )
    ])[0]
    result = attach_cross_chain_features(["0xA", "0xB"], [profile])
    assert result["0xa"]["layerzero_user_tx_count"] == 1
    assert result["0xb"]["layerzero_user_tx_count"] == 0
    assert bridge_activity_score(3, 2, 3) == 15


def test_same_chain_activity_is_not_called_cross_chain():
    event = LayerZeroEvent(
        "0xa", datetime(2024, 1, 1, tzinfo=timezone.utc), 101, 101
    )
    assert not event.cross
