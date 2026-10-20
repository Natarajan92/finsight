"""Validate the observed JSONL schema and select a company without network I/O."""

import json
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .models import DatasetError, Document, Evidence, FinanceBenchDataset, Question
from .paths import cache_path, pdf_path

QUESTIONS_FILE = "financebench_open_source.jsonl"
DOCUMENTS_FILE = "financebench_document_information.jsonl"


def _string(row: dict, key: str, *, nullable: bool = False) -> str | None:
    value = row.get(key)
    if nullable and value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string" + (" or null" if nullable else ""))
    return value


def _integer(row: dict, key: str) -> int:
    value = row.get(key)
    if type(value) is not int or value < 0:
        raise ValueError(f"{key} must be a non-negative integer")
    return value


def _evidence(row: dict) -> Evidence:
    if not isinstance(row, dict):
        raise ValueError("evidence entries must be objects")
    return Evidence(
        doc_name=_string(row, "doc_name"),
        evidence_page_num=_integer(row, "evidence_page_num"),
        evidence_text=_string(row, "evidence_text"),
        evidence_text_full_page=_string(row, "evidence_text_full_page"),
    )


def _question(row: dict) -> Question:
    evidence = row.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("evidence must be a non-empty list")
    return Question(
        **{
            key: _string(row, key)
            for key in (
                "financebench_id",
                "company",
                "doc_name",
                "question",
                "answer",
                "question_type",
                "dataset_subset_label",
            )
        },
        **{
            key: _string(row, key, nullable=True)
            for key in (
                "justification",
                "question_reasoning",
                "domain_question_num",
            )
        },
        evidence=tuple(_evidence(item) for item in evidence),
    )


def _document(row: dict) -> Document:
    return Document(
        **{
            key: _string(row, key)
            for key in (
                "doc_name",
                "company",
                "gics_sector",
                "doc_type",
                "doc_link",
            )
        },
        doc_period=_integer(row, "doc_period"),
    )


def _read_jsonl[T](path: Path, parse: Callable[[dict], T]) -> tuple[T, ...]:
    records = []
    try:
        with path.open(encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    row: Any = json.loads(line)
                    if not isinstance(row, dict):
                        raise ValueError("record must be an object")
                    records.append(parse(row))
                except (ValueError, TypeError, KeyError) as exc:
                    raise DatasetError(f"{path.name}:{line_number}: {exc}") from exc
    except (OSError, UnicodeError) as exc:
        raise DatasetError(f"Cannot read {path}: {exc}. Run the fetch command first.") from exc
    return tuple(records)


def group_documents(documents: tuple[Document, ...]) -> dict[str, list[Document]]:
    grouped = defaultdict(list)
    for document in documents:
        grouped[document.doc_name].append(document)
    return dict(grouped)


def load_dataset(data_dir: Path, company: str = "AMD") -> FinanceBenchDataset:
    """Load local annotations; unresolved references remain visible to the audit."""
    data_dir = Path(data_dir).resolve()
    questions = _read_jsonl(cache_path(data_dir, QUESTIONS_FILE), _question)
    documents = _read_jsonl(cache_path(data_dir, DOCUMENTS_FILE), _document)
    companies = sorted({q.company for q in questions})
    selected = tuple(q for q in questions if q.company.casefold() == company.strip().casefold())
    if not selected:
        raise DatasetError(f"Unknown company {company!r}. Available: {', '.join(companies)}")
    grouped = group_documents(documents)
    names = {name for q in selected for name in (q.doc_name, *(e.doc_name for e in q.evidence))}
    resolved = []
    for name in sorted(names):
        pdf_path(data_dir, name)  # Validate source-derived paths before any file access.
        matches = grouped.get(name, [])
        if len(set(matches)) == 1:
            resolved.append(matches[0])
    return FinanceBenchDataset(
        data_dir,
        selected[0].company,
        selected,
        tuple(resolved),
        questions,
        documents,
    )
