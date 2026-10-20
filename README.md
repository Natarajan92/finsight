# Finsight

A learning-first financial filing RAG project: build an inspectable Python baseline,
evaluate it, then compare advanced retrieval approaches and a LangChain implementation.
The eventual simple UI will accept one SEC filing PDF at a time from any company or year.

**Current module:** PDF ingestion and source locations. The foundation acquires and
audits FinanceBench; ingestion extracts local text PDFs from any company into physical
pages. Retrieval, generation and the UI follow in separately reviewed modules.
No model API keys or Pinecone resources are needed yet.

## Start here

Requirements: [uv](https://docs.astral.sh/uv/) and Python 3.12. `uv` can obtain Python
3.12 if necessary. Commands below run from the repository root in PowerShell.

```powershell
# Keep the package cache local, including in restricted environments.
$env:UV_CACHE_DIR = Join-Path $PWD '.cache/uv'
uv sync --locked

# Explicit network preparation: pinned annotations and the two required AMD PDFs.
uv run python -m finsight.financebench fetch --company AMD

# Offline: inspect references, labels, file presence, and recorded hashes.
uv run python -m finsight.financebench audit --company AMD
```

`fetch` and `audit` accept `--company`, `--data-dir` (default `data/financebench`),
and `--json`. Company names match case-insensitively; quote names containing spaces.
For example, `fetch --company "PepsiCo"` adds its required filings to the same cache.
Only companies with questions in the public sample can be selected.

Fetching an existing verified cache reuses it without HTTP requests. A failed download
is not published as a completed file; successfully recorded earlier downloads can be
reused on the next attempt. If a cached file's hash mismatches, fetch reports an error
and preserves the file. Use a fresh `--data-dir` to acquire a clean copy for comparison.
Unverified pre-existing files are also preserved instead of silently overwritten.

Exit codes: `0` for a successful fetch or an audit without errors, `1` for audit findings
with error severity, `2` for invalid inputs or acquisition/loading failures. Inspect
warnings and `provenance_verified` as well as the audit status. Without a manifest, an
annotation audit can pass while provenance remains explicitly unverified.

## Run the learning notebook

[01_financebench_data_audit.ipynb](notebooks/01_financebench_data_audit.ipynb) covers:

1. Company and document coverage.
2. Questions, gold answers, optional labels, and evidence references.
3. Zero-based page indexes and their display-page interpretation.
4. Reference resolution, metadata conflicts, and provenance.
5. A small company-selection experiment and evaluation limitations.

```powershell
uv run python -m ipykernel install --sys-prefix --name finsight --display-name "Python (finsight)"
uv run jupyter lab
```

Open the notebook, select **Python (finsight)**, and run all cells. An editor with
notebook support can also use this project's `.venv` interpreter. The notebook reads
the already fetched cache. To inspect another cache, set `FINSIGHT_DATA_DIR` before
starting Jupyter or change `DATA_DIR` in its setup cell. Change `COMPANY` to explore
another company; fetching its PDFs remains an explicit command.

The committed notebook has no saved outputs. To execute it from the command line
with outbound HTTP and non-loopback Python socket connections blocked:

```powershell
uv run python scripts/verify_notebook.py
```

The executed copy is saved to `.artifacts/01_financebench_data_audit.executed.ipynb`.
The verifier uses a project-local kernel specification and shuts down its kernel;
it does not need a globally registered Jupyter kernel.

## Module 2: Extract and inspect PDFs

[02_pdf_ingestion.ipynb](notebooks/02_pdf_ingestion.ipynb) covers page provenance,
plain versus layout extraction, pages without text and evidence alignment. It includes
a Mermaid diagram, bounded text previews and a financial-page comparison. Change
`COMPANY` after fetching that company's filings; extraction itself accepts any local PDF.

```powershell
# Generic extraction; parsed text stays in an ignored local artifact.
uv run python -m finsight.ingestion data/financebench/pdfs/AMD_2022_10K.pdf --output .artifacts/pdf-ingestion/amd-pages.json

# Offline evidence-location checks, including source identity and page bounds.
uv run python -m finsight.financebench audit-evidence --company AMD

# Execute Module 2 offline; Module 1 remains the verifier's default.
uv run python scripts/verify_notebook.py --notebook notebooks/02_pdf_ingestion.ipynb
```

The executed copy is `.artifacts/02_pdf_ingestion.executed.ipynb`. Notebook source
files are output-free in Git. Mermaid rendering depends on the notebook viewer;
the diagram's fenced source remains readable when rendering is unavailable.

`extract_pdf(path: Path, *, mode="plain") -> ParsedDocument` records the source filename,
SHA-256, pypdf version, mode, ordered pages and diagnostics. A zero-based physical index
becomes viewer position `index + 1`; printed page labels may differ. Empty and failed
pages retain their positions. The generic extractor never receives benchmark annotations.
Use `--mode layout` to compare spacing; neither mode reconstructs structured tables.

`audit_evidence_locations(dataset, parsed_by_doc) -> EvidenceLocationReport` accounts
for every annotation, checks metadata resolution and source identity, and tests bounds
and text presence. `source_verified` means the parsed snapshot matches the current
cached PDF; `provenance_verified` separately describes the pinned manifest checks.
An absent manifest remains an explicit warning. Pages without text produce warnings;
out-of-range references, failed evidence pages and source mismatches are errors.
Text presence does not establish correct reading order, financial values or answers.

Extraction prints a small JSON summary, optionally exporting full parsed text with
`--output`. It returns `0` for completed extraction, `1` for retained page errors,
and `2` for document/input/output failures. Missing, unreadable, malformed and encrypted
PDFs raise `ExtractionError`; passwords and OCR are outside this module. Evidence audit
uses the same exit conventions as the annotation audit and accepts `--json`.

The inspected AMD cache contains 215 physical pages in the 2015 filing and 121 in the
2022 filing. Both plain extractions had zero no-text or error pages. All nine evidence
annotations cover eight valid document-page locations with text. These checks describe
this cache, not extraction quality across arbitrary uploads. See the
[Module 2 review](docs/superpowers/reviews/2026-10-20-pdf-ingestion-review.md) for observations.

## How Module 1 works

`src/finsight/financebench` separates typed records, source loading, auditing,
cache/manifest handling, acquisition, and the command entry point.

- `load_dataset(data_dir: Path, company: str = "AMD") -> FinanceBenchDataset` validates
  JSONL records, selects questions, and resolves both question and evidence references.
  Records and their optional annotations retain the observed source semantics.
- `audit_dataset(dataset: FinanceBenchDataset) -> AuditReport` counts questions,
  filings, annotations, and unique document-page pairs; it reports missing references,
  duplicates, ambiguous metadata, absent PDFs, and cache integrity failures.
- `fetch_dataset(data_dir: Path, company: str = "AMD") -> Path` fetches pinned sources
  and returns the manifest path. Downloads use temporary files and atomic replacement.

The downloader pins upstream revision
[`cc39aeb4afdf33909ee1412188bf89035950c2eb`](https://github.com/patronus-ai/financebench/tree/cc39aeb4afdf33909ee1412188bf89035950c2eb).
It fetches both annotation JSONL files and only PDFs referenced by the selected questions
and evidence. The manifest records immutable URLs, SHA-256 hashes, sizes, question IDs,
and document names. Hash checks detect changes relative to the recorded download;
they do not prove that benchmark annotations are correct.

Metadata rows are grouped by document name. Identical duplicates resolve to one document.
Conflicting rows are reported rather than choosing one arbitrarily. A conflict required
by the selected company is an error; an unrelated conflict is a warning.

Using explicit standard-library stages makes those choices inspectable before adding
framework integrations. Keeping acquisition separate from loading makes offline
experiments repeatable. A database or a DataFrame library would add little value to this
small initial audit; later modules can introduce tools when an experiment needs them.

## Expected AMD audit

| Quantity | Pinned public sample |
|---|---:|
| Questions | 8 |
| Referenced filings | 2 |
| Evidence annotations | 9 |
| Distinct document-page locations | 8 |
| Questions without reasoning labels | 2 |

The referenced filings are `AMD_2015_10K` and `AMD_2022_10K`. The catalogue includes a
conflicting `FOOTLOCKER_2023_annualreport` metadata entry; the AMD audit reports it as an
unrelated warning. Actual evidence records use `doc_name`, despite the upstream README
describing `evidence_doc_name`. Question IDs are strings, and both reasoning and
justification labels can be null.

## Verification

```powershell
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run python scripts/verify_notebook.py
uv run python scripts/verify_notebook.py --notebook notebooks/02_pdf_ingestion.ipynb
uv build
```

Tests use authored synthetic records, runtime-generated valid PDFs and controlled HTTP
responses. Both notebook tests execute actual notebooks with outbound networking blocked.
Real-data preparation and notebook execution are separate acceptance checks.
Pytest temporary data stays under `.artifacts/pytest`.

To save a local machine-readable audit summary:

```powershell
uv run python -m finsight.financebench audit --json > .artifacts/amd-audit.json
```

## Limitations and review boundary

- Text extraction and evidence bounds checks do not establish that an annotation matches
  parsed text. Visual tables, merged headers, multi-column order and scanned/image pages
  need further work. No text alone does not establish that a page is scanned.
- PDFs are parsed locally in memory for this learning baseline. Resource limits and
  upload isolation belong to the later application flow, before accepting external uploads.
- The eight inspected AMD questions are development cases, not an unseen evaluation set.
  More independently reviewed cases are needed to assess arbitrary uploads.
- Gold evidence identifies known support; it is not an exhaustive relevance set.
  Define valid relevance units and mappings before reporting Recall@k or MRR.
- Keep retrieval evaluation separate from correctness, groundedness, and citation
  evaluation. Label LLM-judge estimates separately from reference-based or human metrics.
  Gold answers and evidence must not become future retrieval/generation inputs.
- Downloads and generated outputs are ignored by Git. The project's MIT license is
  unchanged; external benchmark materials retain their upstream terms.
- Acquisition is a local, single-process development workflow; concurrent writers to
  the same cache are not supported.

Review Module 2 before proceeding to chunking. See the
[Module 2 design](docs/superpowers/specs/2026-10-20-pdf-ingestion-design.md) and
[implementation plan](docs/superpowers/plans/2026-10-20-pdf-ingestion.md).
The [Module 1 design](docs/superpowers/specs/2026-10-20-financebench-foundation-design.md)
and [plan](docs/superpowers/plans/2026-10-20-financebench-foundation.md) remain available.
