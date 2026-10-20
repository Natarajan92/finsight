"""Audit known evidence and corpus readiness without claiming retrieval quality."""

from collections import Counter

from .cache import read_manifest, verify_file
from .loading import DOCUMENTS_FILE, QUESTIONS_FILE, group_documents
from .models import AuditReport, DatasetError, FinanceBenchDataset, Finding
from .paths import pdf_path


def _audit_provenance(dataset: FinanceBenchDataset) -> tuple[bool, list[Finding]]:
    findings = []
    try:
        manifest = read_manifest(dataset.data_dir)
    except DatasetError as exc:
        return False, [Finding("invalid_manifest", "error", "manifest.json", str(exc))]
    if manifest is None:
        return False, [
            Finding(
                "unverified_cache",
                "warning",
                "manifest.json",
                "No manifest: annotation checks are available, but provenance is not verified.",
            )
        ]
    expected = {
        "question_ids": sorted(q.financebench_id for q in dataset.questions),
        "document_names": list(dataset.referenced_doc_names),
    }
    if manifest["selections"].get(dataset.company) != expected:
        findings.append(
            Finding(
                "incomplete_selection",
                "error",
                dataset.company,
                "No completed manifest selection matches these questions and documents. Run fetch.",
            )
        )
    required = [QUESTIONS_FILE, DOCUMENTS_FILE]
    required.extend(f"pdfs/{name}.pdf" for name in dataset.referenced_doc_names)
    for relative in required:
        entry = manifest["files"].get(relative)
        if entry is None:
            findings.append(
                Finding("unverified_file", "error", relative, "No source hash recorded.")
            )
            continue
        try:
            verify_file(dataset.data_dir, relative, entry)
        except DatasetError as exc:
            findings.append(Finding("cache_hash_mismatch", "error", relative, str(exc)))
    return not findings, findings


def audit_dataset(dataset: FinanceBenchDataset) -> AuditReport:
    """Return counts and diagnostics. Warnings do not make the selection unusable."""
    provenance_verified, findings = _audit_provenance(dataset)
    required = set(dataset.referenced_doc_names)
    grouped = group_documents(dataset.all_documents)
    for name, matches in sorted(grouped.items()):
        if len(set(matches)) > 1:
            findings.append(
                Finding(
                    "conflicting_document_metadata",
                    "error" if name in required else "warning",
                    name,
                    "Metadata rows disagree; no row was selected arbitrarily.",
                )
            )
        elif len(matches) > 1:
            findings.append(
                Finding(
                    "duplicate_document_metadata",
                    "warning",
                    name,
                    "Identical metadata rows were collapsed for document resolution.",
                )
            )
    for name in sorted(required):
        if name not in grouped:
            findings.append(
                Finding(
                    "missing_document_metadata",
                    "error",
                    name,
                    "A question or evidence annotation refers to an unknown document.",
                )
            )
        elif any(d.company != dataset.company for d in grouped[name]):
            findings.append(
                Finding(
                    "document_company_mismatch",
                    "error",
                    name,
                    "Required document metadata disagrees with the selected company.",
                )
            )
        if not pdf_path(dataset.data_dir, name).is_file():
            findings.append(Finding("missing_pdf", "error", name, "Run fetch for this company."))
    selected_ids = {q.financebench_id for q in dataset.questions}
    for question_id, count in Counter(q.financebench_id for q in dataset.all_questions).items():
        if count > 1:
            findings.append(
                Finding(
                    "duplicate_question_id",
                    "error" if question_id in selected_ids else "warning",
                    question_id,
                    f"Question ID occurs {count} times.",
                )
            )
    for q in dataset.questions:
        if any(e.doc_name != q.doc_name for e in q.evidence):
            findings.append(
                Finding(
                    "cross_document_evidence",
                    "warning",
                    q.financebench_id,
                    "Evidence spans another filing; a single-PDF evaluation needs this noted.",
                )
            )
    evidence = [e for q in dataset.questions for e in q.evidence]
    return AuditReport(
        company=dataset.company,
        question_count=len(dataset.questions),
        document_count=len(required),
        evidence_count=len(evidence),
        unique_evidence_page_count=len({(e.doc_name, e.evidence_page_num) for e in evidence}),
        missing_reasoning_count=sum(q.question_reasoning is None for q in dataset.questions),
        findings=tuple(findings),
        provenance_verified=provenance_verified,
    )
