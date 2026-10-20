"""Check known support locations; these diagnostics are not retrieval metrics."""

from collections.abc import Mapping
from dataclasses import dataclass

from finsight.ingestion import ParsedDocument

from .auditing import audit_dataset
from .cache import sha256_file
from .models import FinanceBenchDataset, Finding
from .paths import pdf_path


@dataclass(frozen=True, slots=True)
class EvidenceLocation:
    question_id: str
    evidence_index: int
    doc_name: str
    page_index: int
    source_verified: bool
    in_bounds: bool | None
    page_status: str | None
    findings: tuple[Finding, ...]


@dataclass(frozen=True, slots=True)
class EvidenceLocationReport:
    company: str
    annotation_count: int
    unique_location_count: int
    locations: tuple[EvidenceLocation, ...]
    findings: tuple[Finding, ...]
    provenance_verified: bool

    @property
    def text_annotation_count(self) -> int:
        return sum(
            row.source_verified and row.in_bounds is True and row.page_status == "text"
            for row in self.locations
        )

    @property
    def ok(self) -> bool:
        return not any(f.severity == "error" for f in self.findings)


def audit_evidence_locations(
    dataset: FinanceBenchDataset, parsed_by_doc: Mapping[str, ParsedDocument]
) -> EvidenceLocationReport:
    """Verify source identity and bounds, counting each annotation independently.

    Source identity compares extraction with the current cached PDF. The inherited
    corpus audit separately verifies the pinned manifest when one is available.
    Gold answers and evidence text are never compared with extracted text.
    """
    baseline = audit_dataset(dataset)
    findings = list(baseline.findings)
    source_ok = {}
    for name in dataset.referenced_doc_names:
        path = pdf_path(dataset.data_dir, name)
        issues = [
            f
            for f in baseline.findings
            if f.severity == "error" and f.subject in {name, f"pdfs/{name}.pdf"}
        ]
        parsed = parsed_by_doc.get(name)
        if parsed is None:
            issues.append(
                Finding("missing_parsed_document", "error", name, "No extraction supplied.")
            )
        else:
            if parsed.source_filename != path.name:
                issues.append(
                    Finding("source_filename_mismatch", "error", name, "Parsed filename differs.")
                )
            try:
                if parsed.source_sha256 != sha256_file(path):
                    issues.append(
                        Finding(
                            "source_hash_mismatch", "error", name, "Parsed source bytes differ."
                        )
                    )
            except OSError as exc:
                issues.append(Finding("source_unreadable", "error", name, str(exc)))
            if parsed.page_count != len(parsed.pages) or tuple(
                p.page_index for p in parsed.pages
            ) != tuple(range(parsed.page_count)):
                issues.append(
                    Finding("invalid_page_sequence", "error", name, "Physical page indexes differ.")
                )
        findings.extend(f for f in issues if f not in findings)
        source_ok[name] = not issues

    locations = []
    for question in dataset.questions:
        for index, evidence in enumerate(question.evidence):
            name, page_index = evidence.doc_name, evidence.evidence_page_num
            verified = source_ok[name]
            in_bounds = None
            status = None
            issues = []
            subject = f"{question.financebench_id}:evidence[{index}]"
            if verified:
                parsed = parsed_by_doc[name]
                in_bounds = 0 <= page_index < parsed.page_count
                if not in_bounds:
                    issues.append(
                        Finding(
                            "page_out_of_range",
                            "error",
                            subject,
                            f"{name} index {page_index} is outside "
                            f"{parsed.page_count} physical pages.",
                        )
                    )
                else:
                    page = parsed.pages[page_index]
                    status = page.status
                    if status != "text":
                        issues.append(
                            Finding(
                                f"evidence_page_{status}",
                                "error" if status == "error" else "warning",
                                subject,
                                f"{name} index {page_index}: {'; '.join(page.diagnostics)}",
                            )
                        )
            findings.extend(issues)
            locations.append(
                EvidenceLocation(
                    question.financebench_id,
                    index,
                    name,
                    page_index,
                    verified,
                    in_bounds,
                    status,
                    tuple(issues),
                )
            )
    return EvidenceLocationReport(
        dataset.company,
        len(locations),
        len({(row.doc_name, row.page_index) for row in locations}),
        tuple(locations),
        tuple(findings),
        baseline.provenance_verified,
    )
