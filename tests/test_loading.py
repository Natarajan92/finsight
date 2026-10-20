import copy

import pytest
from conftest import document, write_jsonl

from finsight import financebench


def codes(report):
    return {finding.code for finding in report.findings}


def test_loads_selected_questions_with_actual_source_fields(data_dir):
    dataset = financebench.load_dataset(data_dir)
    assert dataset.company == "AMD"
    assert [q.financebench_id for q in dataset.questions] == ["synthetic-1", "synthetic-2"]
    assert dataset.questions[0].evidence[0].doc_name == "AMD_2022_10K"
    assert dataset.questions[0].evidence[0].evidence_page_num == 0
    assert dataset.questions[1].question_reasoning is None
    assert dataset.questions[0].domain_question_num is None
    assert len(dataset.all_questions) == 3
    assert dataset.documents[0].doc_period == 2022


def test_audit_counts_annotations_separately_from_unique_pages(data_dir):
    report = financebench.audit_dataset(financebench.load_dataset(data_dir))
    assert report.ok
    assert report.question_count == 2
    assert report.document_count == 1
    assert report.evidence_count == 3
    assert report.unique_evidence_page_count == 2
    assert report.missing_reasoning_count == 1


def test_preserves_nullable_justification(data_dir, source_records):
    questions, _ = source_records
    questions[0]["justification"] = None
    write_jsonl(data_dir / "financebench_open_source.jsonl", questions)
    assert financebench.load_dataset(data_dir).questions[0].justification is None


def test_selects_another_company_without_amd_specific_logic(data_dir):
    dataset = financebench.load_dataset(data_dir, "other corp")
    assert dataset.company == "Other Corp"
    assert [q.financebench_id for q in dataset.questions] == ["synthetic-3"]
    assert financebench.audit_dataset(dataset).ok


def test_unknown_company_is_not_an_empty_success(data_dir):
    with pytest.raises(financebench.DatasetError, match="Unknown company.*AMD.*Other Corp"):
        financebench.load_dataset(data_dir, "Unknown")


def test_missing_source_file_has_an_actionable_error(tmp_path):
    with pytest.raises(financebench.DatasetError, match="fetch"):
        financebench.load_dataset(tmp_path)


def test_malformed_jsonl_reports_file_and_line(data_dir):
    path = data_dir / "financebench_open_source.jsonl"
    path.write_text(path.read_text(encoding="utf-8") + "{broken\n", encoding="utf-8")
    with pytest.raises(financebench.DatasetError, match="financebench_open_source.jsonl:4"):
        financebench.load_dataset(data_dir)


@pytest.mark.parametrize(
    ("field", "value"),
    [("financebench_id", 17), ("question", None), ("evidence", []), ("company", "")],
)
def test_rejects_invalid_question_fields(data_dir, source_records, field, value):
    questions, _ = source_records
    questions[0][field] = value
    write_jsonl(data_dir / "financebench_open_source.jsonl", questions)
    with pytest.raises(financebench.DatasetError, match=field):
        financebench.load_dataset(data_dir)


@pytest.mark.parametrize("page", [-1, True, 1.5])
def test_rejects_invalid_evidence_page_indexes(data_dir, source_records, page):
    questions, _ = source_records
    questions[0]["evidence"][0]["evidence_page_num"] = page
    write_jsonl(data_dir / "financebench_open_source.jsonl", questions)
    with pytest.raises(financebench.DatasetError, match="evidence_page_num"):
        financebench.load_dataset(data_dir)


def test_does_not_silently_use_readme_evidence_field(data_dir, source_records):
    questions, _ = source_records
    evidence = questions[0]["evidence"][0]
    evidence["evidence_doc_name"] = evidence.pop("doc_name")
    write_jsonl(data_dir / "financebench_open_source.jsonl", questions)
    with pytest.raises(financebench.DatasetError, match="doc_name"):
        financebench.load_dataset(data_dir)


def test_selected_duplicate_ids_are_audit_errors(data_dir, source_records):
    questions, _ = source_records
    questions.append(copy.deepcopy(questions[0]))
    write_jsonl(data_dir / "financebench_open_source.jsonl", questions)
    report = financebench.audit_dataset(financebench.load_dataset(data_dir))
    assert not report.ok
    assert "duplicate_question_id" in codes(report)


def test_missing_metadata_reference_is_an_audit_error(data_dir, source_records):
    _, documents = source_records
    write_jsonl(data_dir / "financebench_document_information.jsonl", documents[1:])
    report = financebench.audit_dataset(financebench.load_dataset(data_dir))
    assert not report.ok
    assert "missing_document_metadata" in codes(report)


def test_resolves_evidence_documents_independently_of_question_document(data_dir, source_records):
    questions, documents = source_records
    questions[0]["evidence"][0]["doc_name"] = "AMD_2021_10K"
    documents.append(document(doc_name="AMD_2021_10K"))
    write_jsonl(data_dir / "financebench_open_source.jsonl", questions)
    write_jsonl(data_dir / "financebench_document_information.jsonl", documents)
    (data_dir / "pdfs" / "AMD_2021_10K.pdf").write_bytes(b"%PDF-1.7\nfixture")
    report = financebench.audit_dataset(financebench.load_dataset(data_dir))
    assert report.ok
    assert report.document_count == 2
    assert "cross_document_evidence" in codes(report)


def test_missing_pdf_is_reported_without_using_the_network(data_dir):
    (data_dir / "pdfs" / "AMD_2022_10K.pdf").unlink()
    report = financebench.audit_dataset(financebench.load_dataset(data_dir))
    assert not report.ok
    assert "missing_pdf" in codes(report)


@pytest.mark.parametrize("selected", [True, False])
def test_conflicting_metadata_blocks_only_required_documents(data_dir, source_records, selected):
    _, documents = source_records
    target = documents[0 if selected else 1]
    documents.append({**target, "doc_period": 2021})
    write_jsonl(data_dir / "financebench_document_information.jsonl", documents)
    report = financebench.audit_dataset(financebench.load_dataset(data_dir))
    assert report.ok is (not selected)
    finding = next(f for f in report.findings if f.code == "conflicting_document_metadata")
    assert finding.severity == ("error" if selected else "warning")


def test_identical_duplicate_metadata_does_not_multiply_documents(data_dir, source_records):
    _, documents = source_records
    documents.append(copy.deepcopy(documents[0]))
    write_jsonl(data_dir / "financebench_document_information.jsonl", documents)
    dataset = financebench.load_dataset(data_dir)
    assert len(dataset.documents) == 1
    report = financebench.audit_dataset(dataset)
    assert report.ok
    assert "duplicate_document_metadata" in codes(report)
