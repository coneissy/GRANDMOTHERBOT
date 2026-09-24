from collections import defaultdict
from decimal import Decimal
from .constants import MAJOR_TOKENS

def token_class(symbol: str) -> str:
    return "Major" if symbol.upper() in MAJOR_TOKENS else "ALT"

def pair_class(token_a: str, token_b: str) -> str:
    a, b = token_class(token_a), token_class(token_b)
    if a == "Major" and b == "Major":
        return "Major-Major"
    if a == "ALT" and b == "ALT":
        return "ALT-ALT"
    return "Major-ALT"

def pair_counts(rows):
    counts=defaultdict(int)
    for row in rows:
        counts[pair_class(row["token_a"],row["token_b"])] += 1
    return dict(counts)

def pair_volumes(rows):
    volumes=defaultdict(Decimal)
    for row in rows:
        volumes[pair_class(row["token_a"],row["token_b"])] += Decimal(str(row["volume_usd"]))
    return dict(volumes)
