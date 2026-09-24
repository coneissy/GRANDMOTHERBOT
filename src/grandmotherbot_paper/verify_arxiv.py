"""CLI for deterministic arXiv provenance verification."""
from __future__ import annotations

import argparse
import json
import sys

from grandmotherbot_paper.arxiv_metadata import (
    ArxivVerificationError,
    load_manifest,
    verify_identifier,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify GrandMotherBot's pinned arXiv paper")
    parser.add_argument("--manifest", default="config/paper_manifest.yaml")
    args = parser.parse_args(argv)

    try:
        manifest = load_manifest(args.manifest)
        paper = manifest["paper"]
        result = verify_identifier(str(paper["identifier"]), paper)
    except (ArxivVerificationError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"ARXIV VERIFICATION ERROR: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
