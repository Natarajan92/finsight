"""Page-addressable extraction records, independent of benchmark annotations."""

from dataclasses import dataclass
from typing import Literal

ExtractionMode = Literal["plain", "layout"]


class ExtractionError(ValueError):
    """A PDF cannot be read as a document, or an extraction option is invalid."""


@dataclass(frozen=True, slots=True)
class ParsedPage:
    page_index: int
    text: str
    status: Literal["text", "no_text", "error"]
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    source_filename: str
    source_sha256: str
    parser_name: str
    parser_version: str
    extraction_mode: ExtractionMode
    page_count: int
    pages: tuple[ParsedPage, ...]
    diagnostics: tuple[str, ...] = ()
