"""Manifest validation and cache integrity, shared by fetch and offline audit."""

import hashlib
import json
import re
from pathlib import Path

from .loading import DOCUMENTS_FILE, QUESTIONS_FILE
from .models import DatasetError
from .paths import cache_path

REVISION = "cc39aeb4afdf33909ee1412188bf89035950c2eb"
BASE_URL = f"https://raw.githubusercontent.com/patronus-ai/financebench/{REVISION}"
MANIFEST_FILE = "manifest.json"


def source_url(relative: str) -> str:
    upstream = relative if relative.startswith("pdfs/") else f"data/{relative}"
    return f"{BASE_URL}/{upstream}"


def sha256_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_manifest(data_dir: Path) -> dict | None:
    path = cache_path(data_dir, MANIFEST_FILE)
    if not path.exists():
        return None
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict) or manifest.get("revision") != REVISION:
            raise ValueError("revision does not match the pinned FinanceBench revision")
        if manifest.get("schema_version") != 1:
            raise ValueError("unsupported manifest schema_version")
        files = manifest.get("files")
        selections = manifest.get("selections")
        if not isinstance(files, dict) or not isinstance(selections, dict):
            raise ValueError("files and selections must be objects")
        for relative, entry in files.items():
            cache_path(data_dir, relative)
            allowed = relative in {QUESTIONS_FILE, DOCUMENTS_FILE} or (
                relative.startswith("pdfs/") and relative.endswith(".pdf")
            )
            if not allowed or not isinstance(entry, dict):
                raise ValueError(f"invalid file entry: {relative}")
            digest = entry.get("sha256")
            size = entry.get("size_bytes")
            if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError(f"invalid sha256 for {relative}")
            if type(size) is not int or size <= 0 or entry.get("url") != source_url(relative):
                raise ValueError(f"invalid size or source URL for {relative}")
        for company, selection in selections.items():
            if not isinstance(company, str) or not isinstance(selection, dict):
                raise ValueError("invalid company selection")
            for key in ("question_ids", "document_names"):
                values = selection.get(key)
                if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
                    raise ValueError(f"invalid selection {key}")
        return manifest
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        raise DatasetError(f"Invalid manifest {path}: {exc}") from exc


def verify_file(data_dir: Path, relative: str, entry: dict) -> None:
    path = cache_path(data_dir, relative)
    try:
        if path.stat().st_size != entry["size_bytes"] or sha256_file(path) != entry["sha256"]:
            raise DatasetError(f"Cache hash mismatch: {relative}. Use a fresh --data-dir.")
    except OSError as exc:
        raise DatasetError(f"Cannot verify cached file {relative}: {exc}") from exc
