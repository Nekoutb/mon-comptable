from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE = re.compile(r"(?<!\d)(?:\+?237)?[ -]?[26](?:[ -]?\d){8}(?!\d)")
BANK = re.compile(r"\b(?:CM\d{25}|\d{18,27})\b", re.I)


@dataclass(frozen=True)
class CorpusCase:
    case_id: str
    document_sha256: str
    document_type: str
    language: str
    quality: str
    supplier_bucket: str
    tax_treatment: str
    page_count: int
    label_status: str
    label_file: str

    @classmethod
    def from_dict(cls, value: dict) -> "CorpusCase":
        case = cls(**value)
        if not re.fullmatch(r"[a-f0-9]{64}", case.document_sha256):
            raise ValueError(f"{case.case_id}: invalid SHA-256")
        if case.page_count < 1:
            raise ValueError(f"{case.case_id}: page_count must be positive")
        if case.label_status not in {"draft", "reviewed", "adjudicated"}:
            raise ValueError(f"{case.case_id}: invalid label status")
        return case


def load_manifest(path: Path) -> list[CorpusCase]:
    cases: list[CorpusCase] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            cases.append(CorpusCase.from_dict(json.loads(line)))
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid corpus manifest line {line_number}: {exc}") from exc
    ids = [case.case_id for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("Corpus case IDs must be unique")
    return cases


def corpus_readiness(cases: Iterable[CorpusCase], minimum: int = 300) -> dict:
    cases = list(cases)
    adjudicated = [case for case in cases if case.label_status == "adjudicated"]
    dimensions = {
        "document_types": len({case.document_type for case in adjudicated}),
        "languages": len({case.language for case in adjudicated}),
        "quality_levels": len({case.quality for case in adjudicated}),
        "supplier_buckets": len({case.supplier_bucket for case in adjudicated}),
        "tax_treatments": len({case.tax_treatment for case in adjudicated}),
    }
    ready = len(adjudicated) >= minimum and dimensions["document_types"] >= 6 and dimensions["languages"] >= 2 and dimensions["quality_levels"] >= 4
    return {"ready": ready, "total": len(cases), "adjudicated": len(adjudicated), "minimum": minimum, "dimensions": dimensions}


def detect_direct_identifiers(text: str) -> list[str]:
    findings = []
    if EMAIL.search(text): findings.append("email")
    if PHONE.search(text): findings.append("phone")
    if BANK.search(text): findings.append("bank_account")
    return findings


def fingerprint(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
