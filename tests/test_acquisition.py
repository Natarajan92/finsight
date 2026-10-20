import hashlib
import io
import json
import urllib.error
import urllib.request
from http.client import IncompleteRead

import pytest
from conftest import write_jsonl

from finsight import financebench

REVISION = "cc39aeb4afdf33909ee1412188bf89035950c2eb"
BASE_URL = f"https://raw.githubusercontent.com/patronus-ai/financebench/{REVISION}"


class Response(io.BytesIO):
    def __init__(self, data: bytes, length: int | None = None):
        super().__init__(data)
        self.headers = {"Content-Length": str(len(data) if length is None else length)}


@pytest.fixture
def remote(data_dir, monkeypatch):
    files = {
        f"{BASE_URL}/data/{name}": (data_dir / name).read_bytes()
        for name in ("financebench_open_source.jsonl", "financebench_document_information.jsonl")
    }
    for path in (data_dir / "pdfs").iterdir():
        files[f"{BASE_URL}/pdfs/{path.name}"] = path.read_bytes()

    def open_response(request, timeout):
        return Response(files[request.full_url])

    monkeypatch.setattr(urllib.request, "urlopen", open_response)
    return files


def test_fetch_records_pinned_provenance_and_only_selected_pdf(tmp_path, remote):
    cache = tmp_path / "cache"
    manifest_path = financebench.fetch_dataset(cache)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["revision"] == REVISION
    assert set(manifest["files"]) == {
        "financebench_open_source.jsonl",
        "financebench_document_information.jsonl",
        "pdfs/AMD_2022_10K.pdf",
    }
    assert manifest["selections"]["AMD"] == {
        "question_ids": ["synthetic-1", "synthetic-2"],
        "document_names": ["AMD_2022_10K"],
    }
    for relative, entry in manifest["files"].items():
        assert entry["sha256"] == hashlib.sha256((cache / relative).read_bytes()).hexdigest()
        upstream = f"{BASE_URL}/{relative if relative.startswith('pdfs/') else 'data/' + relative}"
        assert entry["url"] == upstream
    report = financebench.audit_dataset(financebench.load_dataset(cache))
    assert report.ok
    assert report.provenance_verified


def test_warm_fetch_reuses_cache_without_http(tmp_path, remote, monkeypatch):
    cache = tmp_path / "cache"
    manifest = financebench.fetch_dataset(cache)
    original = manifest.read_bytes()

    def blocked(*args, **kwargs):
        raise AssertionError("Warm fetch must not make HTTP requests")

    monkeypatch.setattr(urllib.request, "urlopen", blocked)
    assert financebench.fetch_dataset(cache).read_bytes() == original


def test_another_company_can_be_added_without_losing_previous_selection(tmp_path, remote):
    cache = tmp_path / "cache"
    financebench.fetch_dataset(cache)
    manifest_path = financebench.fetch_dataset(cache, "Other Corp")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert set(manifest["selections"]) == {"AMD", "Other Corp"}
    assert (cache / "pdfs" / "OTHER_2023_10K.pdf").is_file()
    assert financebench.audit_dataset(financebench.load_dataset(cache)).provenance_verified


@pytest.mark.parametrize("relative", ["pdfs/AMD_2022_10K.pdf", "financebench_open_source.jsonl"])
def test_corrupted_cache_is_rejected_by_fetch_and_audit(tmp_path, remote, relative):
    cache = tmp_path / "cache"
    financebench.fetch_dataset(cache)
    with (cache / relative).open("ab") as stream:
        stream.write(b"\n")
    with pytest.raises(financebench.DatasetError, match="hash"):
        financebench.fetch_dataset(cache)
    report = financebench.audit_dataset(financebench.load_dataset(cache))
    assert not report.ok
    assert not report.provenance_verified
    assert "cache_hash_mismatch" in {f.code for f in report.findings}


def test_interrupted_download_is_not_published_and_can_resume(tmp_path, remote, monkeypatch):
    class Interrupted(Response):
        def read(self, size=-1):
            raise IncompleteRead(b"partial", 100)

    def interrupted(request, timeout):
        if request.full_url.endswith(".pdf"):
            return Interrupted(b"partial")
        return Response(remote[request.full_url])

    cache = tmp_path / "cache"
    monkeypatch.setattr(urllib.request, "urlopen", interrupted)
    with pytest.raises(financebench.DatasetError, match="AMD_2022_10K"):
        financebench.fetch_dataset(cache)
    assert not (cache / "pdfs" / "AMD_2022_10K.pdf").exists()
    assert not list(cache.rglob("*.part"))
    assert not financebench.audit_dataset(financebench.load_dataset(cache)).ok
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda request, timeout: Response(remote[request.full_url]),
    )
    financebench.fetch_dataset(cache)
    assert financebench.audit_dataset(financebench.load_dataset(cache)).provenance_verified


def test_unavailable_pdf_produces_an_explicit_failure(tmp_path, remote, monkeypatch):
    def unavailable(request, timeout):
        if request.full_url.endswith(".pdf"):
            raise urllib.error.HTTPError(request.full_url, 404, "Not Found", {}, None)
        return Response(remote[request.full_url])

    monkeypatch.setattr(urllib.request, "urlopen", unavailable)
    with pytest.raises(financebench.DatasetError, match="AMD_2022_10K.*404"):
        financebench.fetch_dataset(tmp_path / "cache")


@pytest.mark.parametrize("bad_pdf", [b"<html>not a PDF</html>", b""])
def test_non_pdf_responses_are_not_cached(tmp_path, remote, bad_pdf):
    remote[f"{BASE_URL}/pdfs/AMD_2022_10K.pdf"] = bad_pdf
    cache = tmp_path / "cache"
    with pytest.raises(financebench.DatasetError, match="PDF|empty"):
        financebench.fetch_dataset(cache)
    assert not (cache / "pdfs" / "AMD_2022_10K.pdf").exists()


def test_short_response_is_not_accepted_as_a_complete_download(tmp_path, remote, monkeypatch):
    def short_response(request, timeout):
        data = remote[request.full_url]
        return Response(data, len(data) + 20)

    monkeypatch.setattr(urllib.request, "urlopen", short_response)
    with pytest.raises(financebench.DatasetError, match="[Ii]ncomplete"):
        financebench.fetch_dataset(tmp_path / "cache")


def test_manifest_with_escaped_path_is_rejected(tmp_path, remote):
    cache = tmp_path / "cache"
    manifest_path = financebench.fetch_dataset(cache)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"]["../outside.pdf"] = manifest["files"]["pdfs/AMD_2022_10K.pdf"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(financebench.DatasetError, match="[Uu]nsafe|escapes"):
        financebench.fetch_dataset(cache)
    report = financebench.audit_dataset(financebench.load_dataset(cache))
    assert not report.ok
    assert "invalid_manifest" in {f.code for f in report.findings}


def test_unsafe_document_name_cannot_escape_cache(data_dir, source_records):
    questions, documents = source_records
    questions[0]["doc_name"] = "../../outside"
    write_jsonl(data_dir / "financebench_open_source.jsonl", questions)
    with pytest.raises(financebench.DatasetError, match="[Uu]nsafe"):
        financebench.load_dataset(data_dir)


def test_unverified_existing_files_are_not_silently_overwritten(data_dir, remote):
    before = (data_dir / "financebench_open_source.jsonl").read_bytes()
    with pytest.raises(financebench.DatasetError, match="[Uu]nverified"):
        financebench.fetch_dataset(data_dir)
    assert (data_dir / "financebench_open_source.jsonl").read_bytes() == before


def test_selected_ambiguous_metadata_prevents_pdf_acquisition(tmp_path, data_dir, remote):
    relative = "financebench_document_information.jsonl"
    rows = (data_dir / relative).read_bytes()
    conflict = json.loads(rows.splitlines()[0])
    conflict["doc_period"] = 2021
    remote[f"{BASE_URL}/data/{relative}"] = rows + json.dumps(conflict).encode() + b"\n"
    cache = tmp_path / "cache"
    with pytest.raises(financebench.DatasetError, match="[Aa]mbiguous|conflicting"):
        financebench.fetch_dataset(cache)
    assert not (cache / "pdfs" / "AMD_2022_10K.pdf").exists()
