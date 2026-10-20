"""Explicit network acquisition with incremental, atomic cache publication."""

import json
import os
import tempfile
import urllib.error
import urllib.request
from http.client import HTTPException
from pathlib import Path

from .cache import MANIFEST_FILE, REVISION, read_manifest, sha256_file, source_url, verify_file
from .loading import DOCUMENTS_FILE, QUESTIONS_FILE, load_dataset
from .models import DatasetError
from .paths import cache_path


def _save_manifest(data_dir: Path, manifest: dict) -> None:
    target = cache_path(data_dir, MANIFEST_FILE)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=data_dir,
            suffix=".part",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(manifest, stream, indent=2, sort_keys=True)
            stream.write("\n")
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _download(data_dir: Path, relative: str) -> dict:
    path = cache_path(data_dir, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    url = source_url(relative)
    request = urllib.request.Request(url, headers={"User-Agent": "finsight-learning/0.1"})
    temporary = None
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            length = response.headers.get("Content-Length")
            expected = int(length) if length is not None else None
            with tempfile.NamedTemporaryFile(
                dir=path.parent, suffix=".part", delete=False
            ) as stream:
                temporary = Path(stream.name)
                size = 0
                while block := response.read(65536):
                    stream.write(block)
                    size += len(block)
            if not size:
                raise DatasetError(f"Download is empty: {relative}")
            if expected is not None and size != expected:
                raise DatasetError(f"Incomplete download: {relative} ({size}/{expected} bytes)")
        if relative.endswith(".pdf"):
            with temporary.open("rb") as stream:
                if not stream.read(5).startswith(b"%PDF-"):
                    raise DatasetError(f"Response is not a PDF: {relative}")
        entry = {"url": url, "sha256": sha256_file(temporary), "size_bytes": size}
        os.replace(temporary, path)
        return entry
    except (OSError, ValueError, HTTPException) as exc:
        raise DatasetError(f"Failed to acquire {relative}: {exc}") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def fetch_dataset(data_dir: Path, company: str = "AMD") -> Path:
    """Acquire pinned sources. Corrupt or unverified existing files are never overwritten."""
    data_dir = Path(data_dir).resolve()
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        manifest = read_manifest(data_dir) or {
            "schema_version": 1,
            "revision": REVISION,
            "files": {},
            "selections": {},
        }

        def acquire(relative: str) -> None:
            entry = manifest["files"].get(relative)
            if entry is not None:
                verify_file(data_dir, relative, entry)
                return
            if cache_path(data_dir, relative).exists():
                raise DatasetError(
                    f"Unverified cached file: {relative}. Use a fresh --data-dir; "
                    "existing data was not overwritten."
                )
            manifest["files"][relative] = _download(data_dir, relative)
            _save_manifest(data_dir, manifest)

        acquire(QUESTIONS_FILE)
        acquire(DOCUMENTS_FILE)
        dataset = load_dataset(data_dir, company)
        # Missing/ambiguous required metadata must not pick an arbitrary source PDF.
        resolved = {document.doc_name for document in dataset.documents}
        missing = set(dataset.referenced_doc_names) - resolved
        if missing:
            raise DatasetError(
                f"Missing or ambiguous document metadata: {', '.join(sorted(missing))}"
            )
        if any(document.company != dataset.company for document in dataset.documents):
            raise DatasetError("Required document metadata conflicts with the selected company")
        ids = [q.financebench_id for q in dataset.questions]
        if len(ids) != len(set(ids)):
            raise DatasetError("Duplicate question IDs in the selected corpus")
        for name in dataset.referenced_doc_names:
            acquire(f"pdfs/{name}.pdf")
        manifest["selections"][dataset.company] = {
            "question_ids": sorted(ids),
            "document_names": list(dataset.referenced_doc_names),
        }
        _save_manifest(data_dir, manifest)
        return cache_path(data_dir, MANIFEST_FILE)
    except OSError as exc:
        raise DatasetError(f"Cannot acquire dataset in {data_dir}: {exc}") from exc
