"""Explicit acquisition and offline audit: python -m finsight.financebench."""

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from . import DatasetError, audit_dataset, fetch_dataset, load_dataset


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("fetch", "audit"):
        command = commands.add_parser(name)
        command.add_argument("--company", default="AMD")
        command.add_argument("--data-dir", type=Path, default=Path("data/financebench"))
        command.add_argument("--json", action="store_true", help="Print machine-readable results")
    args = parser.parse_args(argv)
    try:
        if args.command == "fetch":
            manifest = fetch_dataset(args.data_dir, args.company)
            print(json.dumps({"manifest": str(manifest)}) if args.json else f"Manifest: {manifest}")
            return 0
        report = audit_dataset(load_dataset(args.data_dir, args.company))
        if args.json:
            print(json.dumps({**asdict(report), "ok": report.ok}, indent=2))
        else:
            print(f"{report.company}: {'PASS' if report.ok else 'FAIL'}")
            for key in (
                "question_count",
                "document_count",
                "evidence_count",
                "unique_evidence_page_count",
                "missing_reasoning_count",
                "provenance_verified",
            ):
                print(f"  {key}: {getattr(report, key)}")
            for finding in report.findings:
                print(
                    f"  {finding.severity.upper()} {finding.code} "
                    f"[{finding.subject}]: {finding.message}"
                )
        return 0 if report.ok else 1
    except DatasetError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
