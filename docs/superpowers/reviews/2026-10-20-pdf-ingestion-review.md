# Module 2 review: PDF ingestion

Implemented on `feat/pdf-ingestion`, based on merged Module 1 at
`18b035f74c37fad7a670f87b9f5549652b2c8c11`.

## Delivered behavior

- Generic `finsight.ingestion` API and CLI, independent of FinanceBench annotations.
- Immutable source/page records, SHA-256, parser version, extraction mode and diagnostics.
- Physical page positions retained for text, no-text and failed pages; plain and layout modes.
- Separate evidence-location audit with source identity, inherited cache/metadata checks,
  bounds checks and one result per annotation, including repeated references.
- Module 2 notebook: 239 explanatory words, Mermaid diagram, bounded previews and a
  plain/layout financial-statement comparison. Verifier supports notebook selection.

## Real-cache observations

Pinned FinanceBench revision: `cc39aeb4afdf33909ee1412188bf89035950c2eb`.
Parser: pypdf 6.21.1, Python 3.12.15, plain extraction.

| Filing | Physical pages | No-text pages | Error pages | Extraction seconds |
|---|---:|---:|---:|---:|
| AMD_2015_10K | 215 | 0 | 0 | 28.953 |
| AMD_2022_10K | 121 | 0 | 0 | 18.868 |

Timings are one local run, not a performance benchmark. All nine evidence annotations
were accounted for at eight distinct document-page locations. Every referenced page was
in bounds and contained text; source identity and manifest verification passed. The
unrelated FOOTLOCKER metadata conflict remains a warning, as in Module 1.

Inspected the 2022 narrative page at index 3 and financial pages at indexes 55 and 57,
plus 2015 statement pages at indexes 55 and 59. Narrative extraction retained headers
and line-wrapped hyphenation. Plain financial text retained numeric sequences,
parentheses and currency symbols in the inspected excerpts, but separated year headers
across lines and flattened column spacing. Layout extraction of the 2022 cash-flow
statement at index 57 aligned the year columns with whitespace. It still produces text,
without typed cells or relationships between headers and values. These observations
do not establish that every financial value or reading order is correct.

Index 57 is viewer position 58; its printed page label is 55. Keeping physical indexes
distinct from printed labels avoids shifting evidence references. The first notebook
run selected a narrative page mentioning cash flows; a failing synthetic regression
now requires the statement heading, and the selection was corrected.

## Verification

- TDD: missing extraction behavior failed 11 tests before implementation; extraction
  tests then passed 13 cases. Missing evidence adapter/command failed 16 cases, then
  passed. Notebook selection and creation failed before implementation.
- The financial-page selection regression failed on narrative index 0, then passed
  on the authored statement at index 2.
- Full suite: **74 passed** (18.37 seconds).
- Ruff lint and format checks: passed across all 32 supported files.
- Both notebooks executed against synthetic fixtures with outbound networking blocked.
- Both notebooks executed offline against the warm AMD cache. Module 1 executed nine
  code cells; Module 2 executed eight (including the verifier's network guard). The final
  Module 2 run compared the cash-flow statement at index 57 and reported 336 total pages,
  zero no-text/error pages, nine text annotations and a passing location audit.
- Wheel and sdist built successfully; archive inspection excluded local datasets, PDFs,
  artifacts, environments and package caches. uv emitted its generic local-cache warning;
  inspection confirmed the cache was absent from both archives.
- User's Module 1 notebook SHA-256 remains
  `dbced3a6640bbdc3d106bc5adda0b948c371b9f6c475ed72a9dfd9c1b64d8c80`.
  Its local saved outputs are excluded from this branch's commits.

Full parsed text, audit JSON, inspected page excerpts and executed notebooks stay in
ignored `.artifacts` paths. Tests generate valid authored PDFs at runtime. Required
source, tests, notebook, lockfile and module documentation are the only intended changes.

## Review and boundary

Fresh whole-branch review covered commits `18b035f..153fee3`: no Critical, Important
or actionable Minor findings. The reviewer independently ran 35 relevant tests, all
passing, and exercised an actually damaged middle-page content stream in both modes.
Both returned `text, error, text`, preserved indexes `0, 1, 2` and extracted the final page.

The reviewer set upload isolation and PDF resource limits aside because this module
provides local extraction. Ruling: retain that approved boundary until the application
flow is implemented. Cost if that boundary is ignored: very large or untrusted PDFs can
consume excessive memory in the local parser. No UI accepts external uploads yet.

No deferred minor findings or additional implementation deviations were identified.

No OCR, structured table recovery, chunking, retrieval, model calls, Pinecone resources
or UI changes were introduced. No new network acquisition was needed for real-cache
verification. Keep this branch for the user's Module 2 review before Module 3.
