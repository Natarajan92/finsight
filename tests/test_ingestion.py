import hashlib
import json
from importlib.metadata import version

import pytest
from pdf_fixtures import write_pdf


def ingestion():
    import finsight.ingestion as api

    return api


@pytest.mark.parametrize("mode", ["plain", "layout"])
def test_extract_preserves_physical_pages_numbers_and_source(tmp_path, mode):
    api = ingestion()
    path = write_pdf(tmp_path / "any_company.pdf", ["Revenue $1,234 (56.78) 9%", None, "Last"])
    parsed = api.extract_pdf(path, mode=mode)
    assert parsed.source_filename == "any_company.pdf"
    assert parsed.source_sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    assert parsed.parser_name == "pypdf"
    assert parsed.parser_version == version("pypdf")
    assert parsed.extraction_mode == mode
    assert parsed.page_count == 3
    assert [p.page_index for p in parsed.pages] == [0, 1, 2]
    assert [p.status for p in parsed.pages] == ["text", "no_text", "text"]
    assert "$1,234 (56.78) 9%" in parsed.pages[0].text
    assert parsed.pages[1].text == ""
    assert parsed.pages[1].diagnostics
    assert "Last" in parsed.pages[2].text


def test_whitespace_is_preserved_but_flagged_as_no_text(tmp_path):
    parsed = ingestion().extract_pdf(write_pdf(tmp_path / "space.pdf", ["   "]))
    assert parsed.pages[0].status == "no_text"
    assert not parsed.pages[0].text.strip()


@pytest.mark.parametrize("kind", ["missing", "malformed", "encrypted", "unreadable"])
def test_document_failures_are_clear_extraction_errors(tmp_path, monkeypatch, kind):
    api = ingestion()
    path = tmp_path / "bad.pdf"
    if kind == "malformed":
        path.write_bytes(b"not a PDF")
    elif kind in {"encrypted", "unreadable"}:
        write_pdf(path, ["Secret"], encrypted=kind == "encrypted")
    if kind == "unreadable":
        from pathlib import Path

        def denied(self):
            raise PermissionError("fixture denied")

        monkeypatch.setattr(Path, "read_bytes", denied)
    with pytest.raises(api.ExtractionError, match="bad.pdf"):
        api.extract_pdf(path)


def test_invalid_extraction_mode_is_rejected(tmp_path):
    api = ingestion()
    with pytest.raises(api.ExtractionError, match="mode"):
        api.extract_pdf(write_pdf(tmp_path / "valid.pdf", ["Text"]), mode="unknown")


def test_failed_page_keeps_its_index_and_later_pages(tmp_path, monkeypatch):
    from pypdf import PageObject

    api = ingestion()
    path = write_pdf(tmp_path / "damaged.pdf", ["First", "Second", "Third"])
    original = PageObject.extract_text

    def extract(self, *args, **kwargs):
        if self.page_number == 1:
            raise ValueError("damaged text stream")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(PageObject, "extract_text", extract)
    parsed = api.extract_pdf(path)
    assert [p.page_index for p in parsed.pages] == [0, 1, 2]
    assert [p.status for p in parsed.pages] == ["text", "error", "text"]
    assert parsed.pages[1].text == ""
    assert "damaged text stream" in parsed.pages[1].diagnostics[0]
    assert "Third" in parsed.pages[2].text


def test_cli_exports_json_without_modifying_pdf(tmp_path, capsys):
    from finsight.ingestion.__main__ import main

    path = write_pdf(tmp_path / "source.pdf", ["Amount 123", None])
    before = path.read_bytes()
    output = tmp_path / "reports/parsed.json"
    assert main([str(path), "--mode", "layout", "--output", str(output)]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["page_count"] == 2
    assert summary["no_text_pages"] == 1
    assert summary["error_pages"] == 0
    exported = json.loads(output.read_text(encoding="utf-8"))
    assert exported["extraction_mode"] == "layout"
    assert "Amount 123" in exported["pages"][0]["text"]
    assert path.read_bytes() == before


def test_cli_reports_bad_pdf_without_traceback(tmp_path, capsys):
    from finsight.ingestion.__main__ import main

    assert main([str(tmp_path / "missing.pdf")]) == 2
    captured = capsys.readouterr()
    assert "missing.pdf" in captured.err
    assert "Traceback" not in captured.err


def test_cli_refuses_to_overwrite_its_source(tmp_path, capsys):
    from finsight.ingestion.__main__ import main

    path = write_pdf(tmp_path / "source.pdf", ["Keep source"])
    before = path.read_bytes()
    assert main([str(path), "--output", str(path)]) == 2
    assert "source" in capsys.readouterr().err.lower()
    assert path.read_bytes() == before


def test_parser_warnings_are_retained_as_diagnostics(tmp_path, monkeypatch):
    import warnings

    from pypdf import PageObject

    original = PageObject.extract_text

    def warn(self, *args, **kwargs):
        warnings.warn("fixture parser warning", UserWarning, stacklevel=2)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(PageObject, "extract_text", warn)
    parsed = ingestion().extract_pdf(write_pdf(tmp_path / "warn.pdf", ["Text"]))
    assert any("fixture parser warning" in d for d in parsed.diagnostics)
