# FinanceBench foundation: approved Module 1 design

Approved in conversation on 20 October 2026. This document preserves the decisions; implementation is limited to Module 1.

## Product direction

Progress from basic to advanced RAG while learning the concepts. The eventual simple UI accepts one text-based SEC filing PDF at a time, from any company and year, and answers with evidence from that document. OCR and multiple-document questions come later. Start with explicit Python stages, then compare a LangChain implementation. Proposed later integrations are Nebius Token Factory embeddings, Pinecone vector search, and Claude generation. Every module includes an executable notebook focused on concepts, inspectable intermediate results, and a small experiment.

## Module 1

Build a company-configurable typed FinanceBench loader, a reproducible local corpus, an audit command, tests, and `notebooks/01_financebench_data_audit.ipynb`. Use AMD as the initial development benchmark. Pin upstream revision `cc39aeb4afdf33909ee1412188bf89035950c2eb`; fetch the two JSONL files and only PDFs referenced by the selected questions and evidence. Record URLs and SHA-256 hashes. Downloads and generated reports are not committed.

Preserve string question IDs, nullable reasoning labels, and zero-based evidence page indexes. Actual evidence records use `doc_name`, despite the README describing `evidence_doc_name`. Resolve question and evidence document references. Report duplicate IDs, missing references, malformed data, and ambiguous metadata. Conflicts outside the selected corpus are visible warnings; required ambiguous references block a clean audit.

Public interfaces: `load_dataset(data_dir: Path, company: str = "AMD") -> FinanceBenchDataset`; `audit_dataset(dataset: FinanceBenchDataset) -> AuditReport`; `fetch_dataset(data_dir: Path, company: str = "AMD") -> Path` (manifest path). Commands: `uv run python -m finsight.financebench fetch --company AMD` and `audit --company AMD`, both accepting `--data-dir` and defaulting to `data/financebench`.

The notebook inspects company coverage, AMD questions and filings, evidence and optional labels, and audit findings. It explores another company and explains valid evaluation claims. It uses the same package as the command workflow and runs against cached data without network access.

## Acceptance and boundaries

Use isolated Python 3.12 with uv, standard-library runtime handling, pytest, Ruff, Jupyter, and nbclient. Tests cover malformed JSONL, incorrect fields, negative pages, duplicate IDs, unknown companies, unresolved and ambiguous references, cache integrity, and interrupted/unavailable downloads. Execute the notebook on synthetic fixtures offline and on the real warm AMD cache.

Expected AMD audit: eight questions, two filings, nine evidence annotations, eight distinct document-page locations, and two missing reasoning labels. These are development examples, not an unseen test set or a reliability guarantee for arbitrary uploads. Evidence annotations identify known support, not exhaustive chunk-level relevance. Gold answers and evidence belong to evaluation, never future retrieval inputs.

No paid APIs, vector resources, PDF parsing, or RAG implementation in Module 1. Page-range and extraction checks begin in Module 2. Keep the existing license. Review this module before approving the next one.
