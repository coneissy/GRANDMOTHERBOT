from __future__ import annotations
import argparse
from pathlib import Path
from .io import load_inputs, validate_inputs
from .constants import PAPER_START_BLOCK, PAPER_END_BLOCK, HORIZONS

def main():
    parser=argparse.ArgumentParser(prog="grandmother-paper")
    sub=parser.add_subparsers(dest="cmd",required=True)
    sub.add_parser("validate")
    a=sub.add_parser("analyze")
    a.add_argument("--input",default="data/input")
    a.add_argument("--output",default="output")
    ns=parser.parse_args()
    if ns.cmd=="validate":
        inputs=load_inputs("data/input")
        errors=validate_inputs(inputs)
        print({"files":sorted(inputs),"errors":errors,"paper_blocks":[PAPER_START_BLOCK,PAPER_END_BLOCK],"horizons":len(HORIZONS)})
        raise SystemExit(1 if errors else 0)
    inputs=load_inputs(ns.input)
    errors=validate_inputs(inputs)
    if errors:
        for e in errors: print(e)
        raise SystemExit(1)
    Path(ns.output).mkdir(parents=True,exist_ok=True)
    for name,df in inputs.items():
        df.to_csv(Path(ns.output)/f"{name}_validated.csv",index=False)
    print(f"Validated {len(inputs)} input datasets. No trading execution is performed.")

if __name__=="__main__":
    main()
