import json
from pathlib import Path

import nbformat
from pdf_fixtures import add_valid_pdfs

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks/02_pdf_ingestion.ipynb"


def test_pdf_notebook_executes_offline_and_preserves_source(data_dir, tmp_path):
    from scripts.verify_notebook import execute_notebook

    output = tmp_path / "02.executed.ipynb"
    protected = (ROOT / "notebooks/01_financebench_data_audit.ipynb").read_bytes()
    before = NOTEBOOK.read_bytes() if NOTEBOOK.exists() else None
    executed = execute_notebook(add_valid_pdfs(data_dir), output, notebook=NOTEBOOK)
    assert output.is_file()
    code = [cell for cell in executed.cells if cell.cell_type == "code"]
    assert all(cell.execution_count is not None for cell in code)
    assert not any(out.output_type == "error" for cell in code for out in cell.outputs)
    summary = json.loads("".join(out.get("text", "") for out in code[-1].outputs))
    assert summary == {
        "company": "AMD",
        "documents": 1,
        "pages": 3,
        "no_text_pages": 1,
        "error_pages": 0,
        "evidence_annotations": 3,
        "unique_evidence_locations": 2,
        "text_annotations": 3,
        "location_audit_ok": True,
    }
    comparison = next(c for c in code if c.source.startswith("COMPARISON_DOC"))
    comparison_text = "".join(out.get("text", "") for out in comparison.outputs)
    assert "AMD_2022_10K: index 2" in comparison_text
    assert "Consolidated Statements of Cash Flows" in comparison_text
    assert NOTEBOOK.read_bytes() == before
    assert (ROOT / "notebooks/01_financebench_data_audit.ipynb").read_bytes() == protected


def test_pdf_notebook_teaches_major_concepts_with_mermaid_and_no_saved_outputs():
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    markdown = "\n".join(c.source for c in notebook.cells if c.cell_type == "markdown")
    assert "```mermaid" in markdown
    assert "not retrieval" in markdown.lower()
    assert len(markdown.split()) < 300
    code = [c for c in notebook.cells if c.cell_type == "code"]
    assert all(c.outputs == [] and c.execution_count is None for c in code)


def test_verifier_refuses_overwriting_its_input_notebook(data_dir, tmp_path):
    import pytest

    from scripts.verify_notebook import execute_notebook

    source = tmp_path / "source.ipynb"
    nbformat.write(nbformat.v4.new_notebook(), source)
    before = source.read_bytes()
    with pytest.raises(ValueError, match="source notebook"):
        execute_notebook(data_dir, source, notebook=source)
    assert source.read_bytes() == before
