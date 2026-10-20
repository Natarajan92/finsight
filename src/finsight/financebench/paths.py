"""Constrain source-derived filenames and manifest paths to the cache."""

from pathlib import Path, PurePosixPath

from .models import DatasetError


def cache_path(data_dir: Path, relative: str) -> Path:
    parts = PurePosixPath(relative)
    if (
        not relative
        or "\\" in relative
        or ":" in relative
        or "\x00" in relative
        or parts.is_absolute()
        or ".." in parts.parts
    ):
        raise DatasetError(f"Unsafe cache path: {relative!r}")
    root = data_dir.resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or path == root:
        raise DatasetError(f"Cache path escapes data directory: {relative!r}")
    return path


def pdf_path(data_dir: Path, doc_name: str) -> Path:
    if not doc_name or any(c in doc_name for c in "/\\:\x00") or doc_name in {".", ".."}:
        raise DatasetError(f"Unsafe document name: {doc_name!r}")
    return cache_path(data_dir, f"pdfs/{doc_name}.pdf")
