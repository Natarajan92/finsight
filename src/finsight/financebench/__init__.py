"""FinanceBench dataset acquisition and inspection."""

from .acquisition import fetch_dataset
from .auditing import audit_dataset
from .evidence import EvidenceLocation, EvidenceLocationReport, audit_evidence_locations
from .loading import load_dataset
from .models import (
    AuditReport,
    DatasetError,
    Document,
    Evidence,
    FinanceBenchDataset,
    Finding,
    Question,
)

__all__ = [
    "AuditReport",
    "DatasetError",
    "Document",
    "Evidence",
    "EvidenceLocation",
    "EvidenceLocationReport",
    "FinanceBenchDataset",
    "Finding",
    "Question",
    "audit_dataset",
    "audit_evidence_locations",
    "fetch_dataset",
    "load_dataset",
]
