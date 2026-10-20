# Module 1: FinanceBench Foundation Implementation Plan

> For agentic workers: use superpowers:executing-plans, test-driven-development, and verification-before-completion. Implement this module only, then pause for review.

**Goal:** build a reproducible dataset loader, corpus audit, and executable learning notebook before retrieval.

**Architecture:** a reusable `src/finsight/financebench` package provides typed loading, auditing, pinned acquisition, and a command entry point. The notebook uses these same functions. Company selection is configurable; AMD is the initial benchmark.

**Tech stack:** Python 3.12, uv, standard library runtime, pytest, Ruff, Jupyter, nbclient.

**Spec:** [Approved design](../specs/2026-10-20-financebench-foundation-design.md).

## Global constraints

- Pin FinanceBench revision `cc39aeb4afdf33909ee1412188bf89035950c2eb`.
- Preserve string IDs, nullable reasoning labels, and zero-based evidence page indexes; evidence uses `doc_name`.
- Downloads and generated reports stay outside Git; keep the MIT license unchanged.
- No model APIs, Pinecone resources, PDF parsing, or retrieval in this module.
- Every module has a learning notebook; the next module needs separate approval.

## Review focus

- Incorrect source schemas, nullable annotations, and malformed records must produce useful diagnostics.
- Ambiguous required documents must not be silently resolved; unrelated conflicts must not block AMD.
- Partial downloads and corrupt caches must not be accepted as a reproducible corpus.
- Unknown companies and unsafe document names must not produce empty success or write outside the cache.
- Notebook execution must remain offline and must not treat evidence as exhaustive retrieval labels.

## Task 1: typed loading and audit

Deliver models for questions, evidence, document metadata, datasets, and audit results, plus company selection and reference resolution. Interfaces: `load_dataset(data_dir: Path, company: str = "AMD") -> FinanceBenchDataset` and `audit_dataset(dataset: FinanceBenchDataset) -> AuditReport`.

- [x] Write synthetic contract tests for actual source fields, optional annotations, malformed JSONL, negative pages, duplicate IDs, unknown companies, missing references, and selected/unselected metadata conflicts.
- [x] Run tests and observe failures before implementation.
- [x] Implement the minimum typed loader and audit, with project configuration folded into this task.
- [x] Run focused tests and lint; record actual results.

Learning objective: distinguish questions, gold answers, evidence, and retrieval relevance.

## Task 2: pinned acquisition and commands

Deliver `fetch_dataset(data_dir: Path, company: str = "AMD") -> Path`, a provenance manifest, cache verification, and `fetch`/`audit` commands with `--company` and `--data-dir`. Fetch both JSONL files and only selected question/evidence PDFs. Record revision, source URLs, file hashes, question IDs, and document names. Cache corruption and failed/incomplete downloads are explicit failures; auditing is offline.

- [x] Write acquisition and command tests with controlled transport responses.
- [x] Observe failures, then implement acquisition and commands.
- [x] Test cache reuse, hash mismatches, interrupted downloads, unavailable files, and path safety.
- [x] Run the task tests and record actual results.

Learning objective: source provenance, caching, and reproducibility.

## Task 3: notebook and documentation

Deliver `notebooks/01_financebench_data_audit.ipynb`, setup instructions, an audit summary, and reproducible verification commands. Cover company coverage, AMD selection, evidence locations, optional annotations, audit findings, another-company exploration, and limitations. Explain concepts and meaningful trade-offs without narrating every Python statement.

- [x] Write an offline notebook execution test using synthetic fixtures.
- [x] Observe failure, then create the notebook using package functions.
- [x] Fetch the real corpus and verify eight questions, two filings, nine evidence annotations, eight unique document-page locations, and two missing reasoning labels.
- [x] Execute the real notebook against the warm cache; run pytest, Ruff, and package build.
- [x] Obtain a final code review, address material findings with regression tests, and report results and limitations.

Learning objective: assess benchmark coverage and the validity of evaluation claims.

## Review boundary

Stop after Module 1. The eight AMD examples are development cases. PDF parsing/page-range validation begins in Module 2. Preserve the actual verification evidence and request the user's module review before continuing.
