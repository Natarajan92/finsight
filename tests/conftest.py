"""Authored synthetic records; no benchmark answers are redistributed."""

import json
import urllib.request
from pathlib import Path

import pytest


def pytest_configure(config):
    (config.rootpath / ".artifacts").mkdir(exist_ok=True)


def question(
    question_id: str = "synthetic-1",
    company: str = "AMD",
    doc_name: str = "AMD_2022_10K",
) -> dict:
    return {
        "financebench_id": question_id,
        "company": company,
        "doc_name": doc_name,
        "question_type": "domain-relevant",
        "question_reasoning": "Information extraction",
        "domain_question_num": None,
        "question": "What is the synthetic revenue?",
        "answer": "$12 million",
        "justification": "The authored fixture states the revenue.",
        "dataset_subset_label": "OPEN_SOURCE",
        "evidence": [
            {
                "evidence_text": "Revenue: $12 million",
                "doc_name": doc_name,
                "evidence_page_num": 0,
                "evidence_text_full_page": "Synthetic page. Revenue: $12 million.",
            }
        ],
    }


def document(company: str = "AMD", doc_name: str = "AMD_2022_10K") -> dict:
    return {
        "doc_name": doc_name,
        "company": company,
        "gics_sector": "Synthetic sector",
        "doc_type": "10k",
        "doc_period": 2022,
        "doc_link": "https://example.invalid/synthetic.pdf",
    }


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in records), encoding="utf-8")


@pytest.fixture(autouse=True)
def no_http(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Tests must use controlled HTTP responses")

    monkeypatch.setattr(urllib.request, "urlopen", blocked)


@pytest.fixture
def source_records():
    first = question()
    second = question("synthetic-2")
    second["question_reasoning"] = None
    second["evidence"].append({**second["evidence"][0], "evidence_page_num": 2})
    other = question("synthetic-3", "Other Corp", "OTHER_2023_10K")
    return [first, second, other], [document(), document("Other Corp", "OTHER_2023_10K")]


@pytest.fixture
def data_dir(tmp_path, source_records):
    questions, documents = source_records
    write_jsonl(tmp_path / "financebench_open_source.jsonl", questions)
    write_jsonl(tmp_path / "financebench_document_information.jsonl", documents)
    pdfs = tmp_path / "pdfs"
    pdfs.mkdir()
    # Acquisition fixtures only. Module 1 does not parse or validate PDF structure.
    for name in ("AMD_2022_10K", "OTHER_2023_10K"):
        (pdfs / f"{name}.pdf").write_bytes(b"%PDF-1.7\nsynthetic acquisition fixture\n%%EOF")
    return tmp_path
