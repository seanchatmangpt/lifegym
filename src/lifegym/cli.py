"""LifeGym command-line verification and RDF export surface."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .factory import export_rdf_text, verify_conformance


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lifegym")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("conform")
    export = sub.add_parser("export-rdf")
    export.add_argument("output", type=Path)
    args = parser.parse_args(argv)

    if args.command == "conform":
        report = verify_conformance()
        print(json.dumps({"conforms": report.conforms, "facts": dict(report.facts), "failures": report.failures}, sort_keys=True))
        return 0 if report.conforms else 2

    if args.command == "export-rdf":
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(export_rdf_text(), encoding="utf-8")
        print(str(args.output))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
