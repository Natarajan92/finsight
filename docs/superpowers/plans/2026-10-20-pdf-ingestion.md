# PDF Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract any text PDF into source-addressable pages and inspect FinanceBench evidence locations.

**Architecture:** A generic ingestion package owns PDF extraction and provenance. A separate FinanceBench adapter checks annotated locations against parsed sources; notebooks exercise these same public functions.

**Tech Stack:** Python 3.12, uv, pypdf, pytest, Ruff, Jupyter and nbclient.

**Spec:** `docs/superpowers/specs/2026-10-20-pdf-ingestion-design.md`

## Global Constraints

- Use plain extraction by default; retain a layout mode for comparison.
- Preserve every physical page, zero-based indexes, extracted text and diagnostics.
- No OCR, structured table reconstruction, chunking, embeddings, model calls, or UI work.
- Keep cached data and generated reports outside Git. Keep the MIT license unchanged.
- Preserve the user's locally executed Module 1 notebook without adding it to commits.
- Keep notebook descriptions short, explaining major concepts with a Mermaid diagram.
- Stop after Module 2 verification and review; Module 3 needs separate authorization.

## Review Focus

- Damaged page streams: preserve the failed page's position and continue subsequent pages.
- Replaced PDFs: reject evidence alignment against a different source hash or filename.
- Empty and whitespace pages: retain locations without claiming that OCR is required.
- Evidence-only document references: resolve evidence's own document and count repeated annotations.
- Notebook failures: preserve source notebooks and shut down the verification kernel.

### Task 1: Generic page extraction

**Files:** Create `src/finsight/ingestion/{__init__,models,pdf,__main__}.py`, `tests/pdf_fixtures.py`, `tests/test_ingestion.py`; modify `pyproject.toml`, `uv.lock`.

**Interfaces:** Produces `extract_pdf(path: Path, *, mode: Literal["plain", "layout"] = "plain") -> ParsedDocument`, immutable `ParsedDocument`/`ParsedPage`, and `ExtractionError`.

- [ ] Add pypdf as the sole new runtime dependency and author valid synthetic PDFs at test runtime.
- [ ] Write failing tests for ordered pages, blank/mixed text, financial numbers, source hash/parser version, plain/layout, missing/unreadable/malformed/encrypted input, invalid mode and page failure continuation. Add CLI JSON export and exit-code tests.
- [ ] Run `uv run --frozen pytest tests/test_ingestion.py -q`. Expected: failures for missing extraction behavior.
- [ ] Implement immutable records, extraction from one byte snapshot, page diagnostics and explicit JSON export CLI. Avoid benchmark imports in ingestion.
- [ ] Repeat focused tests. Expected: all pass. Run full pytest before committing required Task 1 files.

### Task 2: FinanceBench evidence location audit

**Files:** Create `src/finsight/financebench/evidence.py`, `tests/test_evidence_locations.py`; modify `src/finsight/financebench/{__init__,__main__}.py`.

**Interfaces:** Consumes `ParsedDocument` and `FinanceBenchDataset`. Produces `audit_evidence_locations(dataset: FinanceBenchDataset, parsed_by_doc: Mapping[str, ParsedDocument]) -> EvidenceLocationReport` with one result per annotation, plus `audit-evidence` command.

- [ ] Write failing tests for all annotations, repeated locations, evidence-only documents, unresolved metadata/parsed source, source mismatch, missing PDF, invalid indexes and no-text/error pages. Cover CLI success, findings and extraction failure.
- [ ] Run `uv run --frozen pytest tests/test_evidence_locations.py -q`. Expected: missing audit behavior fails.
- [ ] Implement source identity, metadata and physical-page checks; expose counts/findings without similarity or correctness scores. CLI reads cached PDFs offline and prints JSON or human summaries.
- [ ] Repeat focused tests, then full pytest. Expected: all pass. Commit Task 2 source/tests only.

### Task 3: Learning notebook, real-data inspection and review

**Files:** Create `notebooks/02_pdf_ingestion.ipynb`, `tests/test_ingestion_notebook.py`, `docs/superpowers/reviews/2026-10-20-pdf-ingestion-review.md`; modify `scripts/verify_notebook.py`, `README.md`.

**Interfaces:** Extend `execute_notebook(data_dir: Path, output: Path, *, notebook: Path = NOTEBOOK) -> NotebookNode`, preserving Module 1 defaults; CLI adds `--notebook`.

- [ ] Add failing tests for notebook selection, synthetic extraction summary, empty committed outputs and Mermaid content. Run focused tests. Expected: optional notebook argument/notebook missing.
- [ ] Create the notebook with roughly 150–250 explanatory words, bounded previews and a plain/layout financial-page experiment. Generalize the verifier without changing kernel lifecycle.
- [ ] Run synthetic notebook tests and full pytest. Expected: all pass.
- [ ] Parse both cached AMD filings; record page counts, statuses, timings and all nine evidence checks. Inspect narrative and financial statement text, documenting observed limitations.
- [ ] Execute both notebooks offline against the warm cache. Run Ruff lint/format checks, build and inspect archives. Expected: no failures; data/artifacts absent from distributions.
- [ ] Request one fresh read-only branch review under executing-plans. Resolve Important/Critical findings with RED–GREEN tests; record deferred minors and rulings.
- [ ] Record actual validation results, verify the user's Module 1 notebook hash is unchanged, stage only required files and commit. Stop for module review.

## Execution notes

The user's implementation instruction authorizes inline execution of this design. Use native PowerShell ledger bookkeeping in the ignored `.superpowers/sdd/2026-10-20-pdf-ingestion` directory rather than Bash helpers. Keep the existing feature-branch checkout; do not move the user's notebook changes.
