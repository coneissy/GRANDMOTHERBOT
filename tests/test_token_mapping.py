from pathlib import Path

import pytest

from grandmotherbot_extension.token_mapping import (
    CexToken,
    build_contract_index,
    load_cex_tokens,
    resolve_contract,
)


def test_load_cex_tokens_and_resolve(tmp_path: Path):
    path = tmp_path / "cex_tokens.csv"
    path.write_text(
        "symbol,contract_address,source\n"
        "ETH,0x" + "a" * 40 + ",paper\n",
        encoding="utf-8",
    )
    tokens = load_cex_tokens(path)
    index = build_contract_index(tokens)
    resolved = resolve_contract("0x" + "A" * 40, index=index)
    assert resolved is not None
    assert resolved.symbol == "ETH"
    assert resolved.source == "paper"


def test_contract_cannot_map_to_two_symbols():
    address = "0x" + "a" * 40
    with pytest.raises(ValueError):
        build_contract_index([
            CexToken("AAA", address, "paper"),
            CexToken("BBB", address, "paper"),
        ])


def test_unknown_contract_is_not_guessed():
    index = build_contract_index([
        CexToken("AAA", "0x" + "a" * 40, "paper"),
    ])
    assert resolve_contract("0x" + "b" * 40, index=index) is None
