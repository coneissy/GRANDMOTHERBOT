from decimal import Decimal
from dataclasses import dataclass
@dataclass(frozen=True)
class PairClassification:
    token_a:str; token_b:str; category:str; volume_usd:Decimal

def classify_pair(token_a:str,token_b:str,major_tokens:set[str],volume_usd:Decimal)->PairClassification:
    a=token_a.lower() in {x.lower() for x in major_tokens}; b=token_b.lower() in {x.lower() for x in major_tokens}
    category="major-major" if a and b else "major-alt" if a or b else "alt-alt"
    return PairClassification(token_a,token_b,category,volume_usd)
