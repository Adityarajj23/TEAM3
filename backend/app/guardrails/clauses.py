"""Deterministic clause segmentation with stable IDs (e.g. PAY-REQ-001.C1)."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from app.guardrails.quotes import normalize

_BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)]|\([a-z0-9]+\)|[a-z][.)])\s+", re.IGNORECASE)
_SENTENCE_SPLIT = re.compile(r"(?<=[.;!?])\s+(?=[A-Z(\"'])")
_ABBREV = re.compile(r"\b(e\.g|i\.e|etc|vs|approx|No)\.$", re.IGNORECASE)


@dataclass(frozen=True)
class ParsedClause:
    key: str
    position: int
    text: str
    normalized_hash: str


def _sentences(paragraph: str) -> list[str]:
    parts = _SENTENCE_SPLIT.split(paragraph)
    merged: list[str] = []
    for p in parts:
        if merged and _ABBREV.search(merged[-1]):
            merged[-1] = merged[-1] + " " + p
        else:
            merged.append(p)
    return [m.strip() for m in merged if m.strip()]


def split_clauses(requirement_key: str, text: str) -> list[ParsedClause]:
    chunks: list[str] = []
    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if _BULLET.match(line):
            chunks.append(_BULLET.sub("", line).strip())
        else:
            chunks.extend(_sentences(line))
    clauses = []
    for i, chunk in enumerate([c for c in chunks if len(normalize(c)) >= 8], start=1):
        h = hashlib.sha256(normalize(chunk).encode()).hexdigest()
        clauses.append(ParsedClause(f"{requirement_key}.C{i}", i, chunk, h))
    return clauses
