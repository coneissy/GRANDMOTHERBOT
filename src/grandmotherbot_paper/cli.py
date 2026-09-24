from __future__ import annotations

import argparse
from pathlib import Path

from .constants import HORIZONS, PAPER_END_BLOCK, PAPER_START_BLOCK
from .io import load_inputs, validate_inputs
from .report import build_report

def main():
    parser=argparse.ArgumentParser(prog="grandmother-paper")
    sub=parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate")
    a=sub.add_parser("analyze")
    a.add_argument("--input",default="data/input")
    a.add_argument("--output",default="output")
    ns=parser.parse_args()
    root=Path(ns.input)
    if ns.cmd=="validate":
        inputs=load_inputs(root)
        errors=validate_inputs(inputs)
        print({"files":sorted(inputs),"errors":errors,"paper_blocks":[PAPER_START_BLOCK,PAPER_END_BLOCK],"horizons":len(HORIZONS)})
        raise SystemExit(1 if errors else 0)
    inputs=load_inputs(root)
    errors=validate_inputs(inputs)
    if errors:
        for e in errors:
            print(e)
        raise SystemExit(1)
    if not {"transactions","swaps","markouts"}.issubset(inputs):
        raise SystemExit("analyze requires transactions.csv, swaps.csv and markouts.csv")
    summary=build_report(str(root), ns.output)
    print(summary)

if __name__=="__main__":
    main()
