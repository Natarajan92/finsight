# Finsight

A learning-first financial filing RAG project: build an inspectable Python baseline,
evaluate it, then compare advanced retrieval approaches and a LangChain implementation.
The eventual simple UI will accept one SEC filing PDF at a time from any company or year.

**Current module:** FinanceBench data foundation. This module acquires and audits a
benchmark corpus. PDF parsing, retrieval, generation, and the UI follow in separately
reviewed modules. No model API keys or Pinecone resources are needed yet.

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
uv build
```

Tests use authored synthetic records and controlled HTTP responses. The notebook test
executes the actual notebook against those fixtures with outbound networking blocked.
Real-data preparation and notebook execution are separate acceptance checks.
Pytest temporary data stays under `.artifacts/pytest`.

To save a local machine-readable audit summary:

```powershell
uv run python -m finsight.financebench audit --json > .artifacts/amd-audit.json
```

## Limitations and review boundary

- This module checks annotations and acquisition. It does not parse PDFs, check page
  bounds, inspect table extraction, or verify that evidence matches downloaded page text.
  PDF signature checks during acquisition are not full structural validation.
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

Review Module 1 before proceeding to PDF parsing in Module 2.
See the [approved design](docs/superpowers/specs/2026-10-20-financebench-foundation-design.md)
and [implementation plan](docs/superpowers/plans/2026-10-20-financebench-foundation.md).
