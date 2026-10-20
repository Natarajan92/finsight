"""Explicit acquisition and offline audit: python -m finsight.financebench."""

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from finsight.ingestion import ExtractionError, extract_pdf

from . import DatasetError, audit_dataset, audit_evidence_locations, fetch_dataset, load_dataset
from .paths import pdf_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("fetch", "audit", "audit-evidence"):
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
        dataset = load_dataset(args.data_dir, args.company)
        if args.command == "audit-evidence":
            parsed = {
                name: extract_pdf(pdf_path(dataset.data_dir, name))
                for name in dataset.referenced_doc_names
            }
            report = audit_evidence_locations(dataset, parsed)
            counts = ("annotation_count", "unique_location_count", "text_annotation_count")
        else:
            report = audit_dataset(dataset)
            counts = (
                "question_count",
                "document_count",
                "evidence_count",
                "unique_evidence_page_count",
                "missing_reasoning_count",
            )
        if args.json:
            result = {**asdict(report), "ok": report.ok}
            if args.command == "audit-evidence":
                result["text_annotation_count"] = report.text_annotation_count
            print(json.dumps(result, indent=2))
        else:
            print(f"{report.company}: {'PASS' if report.ok else 'FAIL'}")
            for key in (*counts, "provenance_verified"):
                print(f"  {key}: {getattr(report, key)}")
            for finding in report.findings:
                print(
                    f"  {finding.severity.upper()} {finding.code} "
                    f"[{finding.subject}]: {finding.message}"
                )
        return 0 if report.ok else 1
    except (DatasetError, ExtractionError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
