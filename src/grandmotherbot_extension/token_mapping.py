from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CexToken:
    symbol: str
    contract_address: str
    source: str


def load_cex_tokens(path: str | Path) -> list[CexToken]:
    target = Path(path)
    with target.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"symbol", "contract_address", "source"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            missing = required - set(reader.fieldnames or ())
            raise ValueError("cex_tokens.csv missing: " + ", ".join(sorted(missing)))

        tokens = []
        for row in reader:
            symbol = str(row["symbol"]).strip().upper()
            address = str(row["contract_address"]).strip().lower()
            source = str(row["source"]).strip()
            if not symbol or not address or not source:
                raise ValueError("cex_tokens.csv contains an incomplete row")
            if not address.startswith("0x") or len(address) != 42:
                raise ValueError(f"invalid ERC-20 contract address: {address}")
            tokens.append(CexToken(symbol=symbol, contract_address=address, source=source))
    return tokens


def build_contract_index(tokens: list[CexToken]) -> dict[str, CexToken]:
    index: dict[str, CexToken] = {}
    for token in tokens:
        existing = index.get(token.contract_address)
        if existing is not None and existing.symbol != token.symbol:
            raise ValueError(
                "one contract maps to multiple CEX symbols: "
                f"{token.contract_address}: {existing.symbol}, {token.symbol}"
            )
        index[token.contract_address] = token
    return index


def resolve_contract(
    contract_address: str,
    *,
    index: dict[str, CexToken],
) -> CexToken | None:
    return index.get(contract_address.strip().lower())
