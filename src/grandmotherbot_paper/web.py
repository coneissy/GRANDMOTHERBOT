from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .io import load_inputs, validate_inputs


def _status() -> dict:
    root = Path("data/input")
    required = ("transactions.csv", "swaps.csv", "markouts.csv")
    present = {name: (root / name).is_file() for name in required}
    inputs = load_inputs(root)
    errors = validate_inputs(inputs) if inputs else []
    return {
        "service": "GrandMother",
        "mode": "research_replication",
        "live_trading": False,
        "required_inputs": present,
        "inputs_valid": not errors,
        "validation_errors": errors,
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "GrandMother/0.1"

    def _send(self, status: int, body: dict) -> None:
        payload = json.dumps(body, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in {"/", "/health"}:
            self._send(200, _status())
            return
        if path == "/status":
            self._send(200, _status())
            return
        self._send(404, {"error": "not_found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path != "/analyze":
            self._send(404, {"error": "not_found"})
            return

        root = Path("data/input")
        status = _status()
        if not status["inputs_valid"] or not all(status["required_inputs"].values()):
            self._send(
                409,
                {
                    "error": "normalized research inputs are not ready",
                    **status,
                },
            )
            return

        from .report import build_report

        output = os.environ.get("GRANDMOTHER_OUTPUT_DIR", "output")
        summary = build_report(str(root), output)
        self._send(200, {"status": "analysis_complete", "summary": summary})


def main() -> None:
    port = int(os.environ.get("PORT", "10000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"GrandMother research service listening on 0.0.0.0:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
