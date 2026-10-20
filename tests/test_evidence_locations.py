import json
from dataclasses import replace

import pytest
from pdf_fixtures import add_valid_pdfs, write_pdf

from finsight.financebench import load_dataset
from finsight.ingestion import extract_pdf


@pytest.fixture
def corpus(data_dir):
    dataset = load_dataset(add_valid_pdfs(data_dir))
    parsed = {
        name: extract_pdf(data_dir / f"pdfs/{name}.pdf") for name in dataset.referenced_doc_names
    }
    return dataset, parsed


def audit(dataset, parsed):
    from finsight.financebench import audit_evidence_locations

    return audit_evidence_locations(dataset, parsed)


def test_all_annotations_counted_including_repeated_page(corpus):
    dataset, parsed = corpus
    report = audit(dataset, parsed)
    assert report.ok
    assert report.annotation_count == 3
    assert report.unique_location_count == 2
    assert report.text_annotation_count == 3
    assert [(r.question_id, r.evidence_index, r.page_index) for r in report.locations] == [
        ("synthetic-1", 0, 0),
        ("synthetic-2", 0, 0),
        ("synthetic-2", 1, 2),
    ]
    assert all(
        r.source_verified and r.in_bounds and r.page_status == "text" for r in report.locations
    )


@pytest.mark.parametrize("index", [-1, 3])
def test_out_of_range_evidence_is_not_a_python_list_lookup(corpus, index):
    dataset, parsed = corpus
    q = dataset.questions[0]
    changed = replace(q, evidence=(replace(q.evidence[0], evidence_page_num=index),))
    report = audit(replace(dataset, questions=(changed,)), parsed)
    assert not report.ok
    assert report.locations[0].in_bounds is False
    assert report.locations[0].page_status is None
    assert "page_out_of_range" in {f.code for f in report.findings}


@pytest.mark.parametrize("status", ["no_text", "error"])
def test_page_diagnostics_do_not_claim_text_correctness(corpus, status):
    dataset, parsed = corpus
    q = dataset.questions[0]
    index = 1 if status == "no_text" else 0
    if status == "error":
        doc = parsed[q.doc_name]
        failed = replace(doc.pages[0], text="", status="error", diagnostics=("damaged",))
        parsed[q.doc_name] = replace(doc, pages=(failed, *doc.pages[1:]))
    changed = replace(q, evidence=(replace(q.evidence[0], evidence_page_num=index),))
    report = audit(replace(dataset, questions=(changed,)), parsed)
    assert report.locations[0].in_bounds
    assert report.locations[0].page_status == status
    assert report.text_annotation_count == 0
    assert f"evidence_page_{status}" in {f.code for f in report.findings}
    assert report.ok is (status == "no_text")


@pytest.mark.parametrize("problem", ["hash", "filename", "missing_parse", "missing_pdf", "indexes"])
def test_unverified_source_cannot_pass_alignment(corpus, problem):
    dataset, parsed = corpus
    name = dataset.referenced_doc_names[0]
    doc = parsed[name]
    if problem == "hash":
        write_pdf(dataset.data_dir / f"pdfs/{name}.pdf", ["Replacement"])
    elif problem == "filename":
        parsed[name] = replace(doc, source_filename="another.pdf")
    elif problem == "missing_parse":
        parsed.clear()
    elif problem == "missing_pdf":
        (dataset.data_dir / f"pdfs/{name}.pdf").unlink()
    else:
        parsed[name] = replace(doc, pages=(doc.pages[2], doc.pages[1], doc.pages[0]))
    report = audit(dataset, parsed)
    assert not report.ok
    assert report.text_annotation_count == 0
    assert not any(row.source_verified for row in report.locations)


@pytest.mark.parametrize("conflicting", [False, True])
def test_unresolved_or_ambiguous_selected_metadata_blocks(corpus, conflicting):
    dataset, parsed = corpus
    selected = dataset.documents[0]
    metadata = (
        (*dataset.all_documents, replace(selected, doc_period=1999))
        if conflicting
        else tuple(d for d in dataset.all_documents if d.doc_name != selected.doc_name)
    )
    report = audit(replace(dataset, all_documents=metadata, documents=()), parsed)
    assert not report.ok
    assert not any(row.source_verified for row in report.locations)


def test_evidence_resolves_its_own_document_and_gold_text_is_not_compared(data_dir, source_records):
    from conftest import document, write_jsonl

    questions, documents = source_records
    questions[0]["evidence"][0]["doc_name"] = "AMD_2015_10K"
    questions[0]["evidence"][0]["evidence_text"] = "Different gold wording"
    questions[0]["answer"] = "Gold answer deliberately unrelated to parsed text"
    write_jsonl(data_dir / "financebench_open_source.jsonl", questions)
    write_jsonl(
        data_dir / "financebench_document_information.jsonl",
        [*documents, document(doc_name="AMD_2015_10K")],
    )
    write_pdf(data_dir / "pdfs/AMD_2015_10K.pdf", ["Earlier filing"])
    dataset = load_dataset(add_valid_pdfs(data_dir))
    parsed = {
        name: extract_pdf(data_dir / f"pdfs/{name}.pdf") for name in dataset.referenced_doc_names
    }
    report = audit(dataset, parsed)
    assert report.ok
    assert report.locations[0].doc_name == "AMD_2015_10K"
    assert report.locations[0].source_verified
    assert report.text_annotation_count == 3


@pytest.mark.parametrize("problem", [None, "bounds", "malformed"])
def test_evidence_cli_runs_offline_and_reports_failures(data_dir, source_records, capsys, problem):
    from conftest import write_jsonl

    from finsight.financebench.__main__ import main

    add_valid_pdfs(data_dir)
    if problem == "bounds":
        questions, _ = source_records
        questions[0]["evidence"][0]["evidence_page_num"] = 10
        write_jsonl(data_dir / "financebench_open_source.jsonl", questions)
    elif problem == "malformed":
        (data_dir / "pdfs/AMD_2022_10K.pdf").write_bytes(b"invalid")
    code = main(["audit-evidence", "--company", "AMD", "--data-dir", str(data_dir), "--json"])
    captured = capsys.readouterr()
    assert code == {None: 0, "bounds": 1, "malformed": 2}[problem]
    if problem == "malformed":
        assert "AMD_2022_10K.pdf" in captured.err
        assert "Traceback" not in captured.err
    else:
        result = json.loads(captured.out)
        assert result["annotation_count"] == 3
        assert result["ok"] is (problem is None)
