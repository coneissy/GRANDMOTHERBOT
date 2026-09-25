from dataclasses import dataclass
@dataclass(frozen=True)
class BenchmarkCount:
    name:str; observed:int; expected:int
    @property
    def difference(self): return self.observed-self.expected
    @property
    def passed(self): return self.difference==0
PAPER_COUNTS={"detected":8723233,"missing_tardis":163148,"inventory_adjustment":683539,"final_arbitrages":7203560}
def reconcile(counts:dict[str,int]): return [BenchmarkCount(k,counts.get(k,0),v) for k,v in PAPER_COUNTS.items()]
