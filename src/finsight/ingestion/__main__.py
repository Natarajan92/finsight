"""Extract a local text PDF: python -m finsight.ingestion FILE.pdf [--output REPORT.json]."""

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from . import ExtractionError, extract_pdf


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--mode", choices=("plain", "layout"), default="plain")
    parser.add_argument("--output", type=Path, help="Write full parsed text and provenance as JSON")
    args = parser.parse_args(argv)
    try:
        if args.output and (
            args.output.resolve() == args.pdf.resolve()
            or (args.output.exists() and args.pdf.exists() and args.output.samefile(args.pdf))
        ):
            raise ExtractionError("Output must differ from the source PDF")
        parsed = extract_pdf(args.pdf, mode=args.mode)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(asdict(parsed), indent=2), encoding="utf-8")
        no_text = sum(p.status == "no_text" for p in parsed.pages)
        errors = sum(p.status == "error" for p in parsed.pages)
        print(
            json.dumps(
                {
                    "source_filename": parsed.source_filename,
                    "source_sha256": parsed.source_sha256,
                    "page_count": parsed.page_count,
                    "no_text_pages": no_text,
                    "error_pages": errors,
                    "diagnostics": parsed.diagnostics,
                    "output": str(args.output) if args.output else None,
                },
                indent=2,
            )
        )
        return 1 if errors else 0
    except (ExtractionError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
