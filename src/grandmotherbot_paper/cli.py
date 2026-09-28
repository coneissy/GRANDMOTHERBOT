from __future__ import annotations

import argparse
from pathlib import Path

from .constants import HORIZONS, PAPER_END_BLOCK, PAPER_START_BLOCK
from .io import load_inputs, validate_inputs
from .report import build_report

def main():
    parser=argparse.ArgumentParser(prog="grandmother-paper")
    sub=parser.add_subparsers(dest="cmd", required=True)
    v=sub.add_parser("validate")
    v.add_argument("--input",default="data/input")
    sub.add_parser("serve")
    a=sub.add_parser("analyze")
    a.add_argument("--input",default="data/input")
    a.add_argument("--output",default="output")
    ns=parser.parse_args()
    if ns.cmd=="serve":
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        import os

        class HealthHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path not in {"/", "/health"}:
                    self.send_response(404)
                    self.end_headers()
                    return
                body=b'{"status":"ok","service":"grandmother-research"}\n'
                self.send_response(200)
                self.send_header("Content-Type","application/json")
                self.send_header("Content-Length",str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            def log_message(self, format, *args):
                return

        port=int(os.environ.get("PORT","10000"))
        ThreadingHTTPServer(("0.0.0.0",port),HealthHandler).serve_forever()
        return
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
