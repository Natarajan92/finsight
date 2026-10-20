"""Extract one immutable source snapshot; retain physical page positions."""

import hashlib
import io
import logging
import warnings
from importlib.metadata import version
from pathlib import Path

from pypdf import PdfReader

from .models import ExtractionError, ExtractionMode, ParsedDocument, ParsedPage


class _Diagnostics(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


def extract_pdf(path: Path, *, mode: ExtractionMode = "plain") -> ParsedDocument:
    """Extract text without cleaning, OCR or table reconstruction.

    Document failures raise ExtractionError. A failed page remains in the result
    with empty text and an error diagnostic; subsequent pages are still attempted.
    """
    if mode not in {"plain", "layout"}:
        raise ExtractionError(f"{path.name}: unsupported extraction mode {mode!r}")
    try:
        source = path.read_bytes()
    except OSError as exc:
        raise ExtractionError(f"Cannot read {path}: {exc}") from exc
    diagnostics = _Diagnostics()
    logger = logging.getLogger("pypdf")
    logger.addHandler(diagnostics)
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            reader = PdfReader(io.BytesIO(source), strict=False)
            if reader.is_encrypted:
                raise ExtractionError(f"{path.name}: encrypted PDFs are not supported")
            pages = []
            for index, page in enumerate(reader.pages):
                try:
                    text = page.extract_text(extraction_mode=mode) or ""
                    status = "text" if text.strip() else "no_text"
                    notes = () if status == "text" else ("No extractable text; inspect the page.",)
                    pages.append(ParsedPage(index, text, status, notes))
                except Exception as exc:
                    # A damaged content stream must not shift later source locations.
                    pages.append(ParsedPage(index, "", "error", (f"{type(exc).__name__}: {exc}",)))
            messages = (*diagnostics.messages, *(str(w.message) for w in caught))
    except ExtractionError:
        raise
    except Exception as exc:
        raise ExtractionError(f"Cannot parse {path.name}: {type(exc).__name__}: {exc}") from exc
    finally:
        logger.removeHandler(diagnostics)
        diagnostics.close()
    return ParsedDocument(
        source_filename=path.name,
        source_sha256=hashlib.sha256(source).hexdigest(),
        parser_name="pypdf",
        parser_version=version("pypdf"),
        extraction_mode=mode,
        page_count=len(pages),
        pages=tuple(pages),
        diagnostics=tuple(messages),
    )
