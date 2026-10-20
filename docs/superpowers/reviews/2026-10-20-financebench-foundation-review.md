# Module 1 implementation and learning review

## Outcome and approach

Implemented typed FinanceBench loading, a company-configurable corpus audit, pinned
acquisition with a provenance manifest, fetch/audit commands, and an executable notebook.
No paid model calls or Pinecone resources were used. The implementation is on
`feat/financebench-foundation`; Module 2 has not started.

The loader validates source records and selects a company. Document metadata is grouped
by document name: identical rows collapse to one result; conflicting rows remain
unresolved and visible. Question and evidence references are both checked. The audit
counts evidence annotations separately from distinct document-page locations.

Acquisition uses immutable source URLs and records hashes and sizes. Each download is
written to a temporary file, checked, then atomically published. The manifest is updated
incrementally so interrupted preparation can resume from recorded successful files.
Loading and auditing perform no network requests.

Explicit standard-library stages make the behavior easy to inspect and reuse from the
notebook and command. DataFrames could make larger exploratory analysis more convenient;
they are unnecessary for this initial corpus. A database would add persistence and query
capabilities at a dependency and operational cost that this stage does not need.

## Verification evidence

- `uv run --frozen pytest -q --tb=short`: **42 passed**.
- `uv run --frozen ruff check .`: **passed**.
- `uv run --frozen ruff format --check .`: **19 files already formatted**.
- `uv run --frozen python scripts/verify_notebook.py`: **all 9 code cells executed**
  against the real warm AMD cache with outbound HTTP and ordinary non-loopback Python
  socket connections blocked.
- Notebook tests execute the actual notebook on authored synthetic fixtures and verify
  kernel shutdown on both success and failure. The shutdown tests failed before the
  cleanup fix. The documented pytest entry point exposed an import-path discrepancy;
  the full suite passed after configuring the test path.
- `uv build`: **wheel and source distribution built**. Archive inspection found no
  downloaded data or local artifacts (13 wheel entries; 26 source-distribution entries).
- Real AMD audit: **8 questions, 2 filings, 9 evidence annotations, 8 distinct evidence
  pages, 2 missing reasoning labels; provenance verified**. An unrelated conflicting
  Foot Locker metadata entry appears as a warning.
- The source notebook remains output-free; executed output and the machine-readable
  audit are local artifacts. The original license is unchanged.

## Decisions and execution adaptations

- Used a feature branch in the existing workspace. This preserves the main branch and
  keeps files directly reviewable here; it does not provide a separate worktree checkout.
- Used a native Windows execution ledger instead of Bash-oriented skill helpers.
  Progress bookkeeping was manual; tests and commands remained executable evidence.
- Preserved nullable justification in addition to reasoning after inspecting the actual
  source. Requiring a string would reject real records; preserving null avoids invented labels.
- Allowed annotation-only auditing without a manifest, with an explicit warning and
  `provenance_verified=False`. Such an `ok` result does not certify source provenance;
  inspect both fields. Real acquisition produces and verifies a manifest.

## Independent code review

A fresh-context, read-only review inspected the design, plan, implementation, tests,
notebook, documentation, and local source schema. It found **no Critical or Important
issues** and assessed the module as ready for user review.

One Minor issue is deferred: fetch checks question-ID duplicates within the selected
company; audit additionally catches selected IDs duplicated across companies. Thus a
modified dataset with a cross-company ID collision can finish fetching but fail its
subsequent audit. The pinned public sample has no duplicate question IDs. Keep the
documented fetch-then-audit workflow. A future fix should use global ID counts intersected
with selected IDs and add a collision regression test.

The reviewer left PDF structure, page bounds, extraction, and answer correctness to later
modules, as designed. Concurrent cache writers remain unsupported and documented. The
offline guard is verification instrumentation for this known notebook, not a general
security sandbox for arbitrary code. Final archive inspection was performed by the main
agent. These boundaries leave PDF content quality and broader evaluation unverified.

## Learning experiment and next review

Run the notebook, then change `OTHER_COMPANY` in its experiment cell. Explain why another
company's questions can be available in the JSONL files while its PDFs and completed
manifest selection are absent. Compare question counts, years, reasoning labels, and
known evidence locations. Fetching that company's PDFs remains a separate explicit step.

The eight inspected AMD cases are development examples. Their evidence identifies known
support without providing exhaustive retrieval relevance. No retrieval or generation
quality claims have been made. Review this module and notebook before approving
Module 2: PDF extraction and source-location preservation.
