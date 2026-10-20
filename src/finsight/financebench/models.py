"""Source-shaped records: annotations stay distinct from document content."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


class DatasetError(ValueError):
    """The corpus cannot be loaded or acquired safely and reproducibly."""


@dataclass(frozen=True, slots=True)
class Evidence:
    doc_name: str
    evidence_page_num: int
    evidence_text: str
    evidence_text_full_page: str


@dataclass(frozen=True, slots=True)
class Question:
    financebench_id: str
    company: str
    doc_name: str
    question: str
    answer: str
    justification: str | None
    question_type: str
    question_reasoning: str | None
    domain_question_num: str | None
    dataset_subset_label: str
    evidence: tuple[Evidence, ...]


@dataclass(frozen=True, slots=True)
class Document:
    doc_name: str
    company: str
    gics_sector: str
    doc_type: str
    doc_period: int
    doc_link: str


@dataclass(frozen=True, slots=True)
class FinanceBenchDataset:
    data_dir: Path
    company: str
    questions: tuple[Question, ...]
    documents: tuple[Document, ...]
    all_questions: tuple[Question, ...]
    all_documents: tuple[Document, ...]

    @property
    def referenced_doc_names(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    name
                    for question in self.questions
                    for name in (question.doc_name, *(e.doc_name for e in question.evidence))
                }
            )
        )


@dataclass(frozen=True, slots=True)
class Finding:
    code: str
    severity: Literal["error", "warning"]
    subject: str
    message: str


@dataclass(frozen=True, slots=True)
class AuditReport:
    company: str
    question_count: int
    document_count: int
    evidence_count: int
    unique_evidence_page_count: int
    missing_reasoning_count: int
    findings: tuple[Finding, ...]
    provenance_verified: bool = False

    @property
    def ok(self) -> bool:
        return not any(f.severity == "error" for f in self.findings)
