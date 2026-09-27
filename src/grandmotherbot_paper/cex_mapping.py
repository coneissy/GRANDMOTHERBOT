from dataclasses import dataclass
from decimal import Decimal
import re

_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")


@dataclass(frozen=True)
class BinanceToken:
    symbol: str
    contract_address: str
    decimals: int | None = None

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError("token symbol must be non-empty")
        if not _ADDRESS_RE.fullmatch(self.contract_address):
            raise ValueError(f"invalid Ethereum contract address: {self.contract_address}")
        if self.decimals is not None and not 0 <= self.decimals <= 255:
            raise ValueError("token decimals must be between 0 and 255")


@dataclass(frozen=True)
class TokenMatch:
    contract_address: str
    symbol: str
    matched: bool
    reason: str


def normalize_address(address: str) -> str:
    value = str(address).strip()
    if not _ADDRESS_RE.fullmatch(value):
        raise ValueError(f"invalid Ethereum contract address: {address}")
    return value.lower()


def build_contract_index(tokens: list[BinanceToken]) -> dict[str, BinanceToken]:
    index: dict[str, BinanceToken] = {}
    for token in tokens:
        key = normalize_address(token.contract_address)
        if key in index and index[key].symbol != token.symbol:
            raise ValueError(
                f"contract maps to multiple Binance symbols: {token.contract_address}"
            )
        index[key] = token
    return index


def match_contract(address: str, index: dict[str, BinanceToken]) -> TokenMatch:
    key = normalize_address(address)
    token = index.get(key)
    if token is None:
        return TokenMatch(key, "", False, "not_in_binance_universe")
    return TokenMatch(key, token.symbol, True, "contract_exact_match")


def map_effective_pair(
    token_bought_contract: str,
    token_sold_contract: str,
    index: dict[str, BinanceToken],
) -> tuple[TokenMatch, TokenMatch]:
    bought = match_contract(token_bought_contract, index)
    sold = match_contract(token_sold_contract, index)
    return bought, sold
