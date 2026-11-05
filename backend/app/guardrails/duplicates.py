"""Duplicate / near-duplicate detection using token Jaccard similarity."""
from __future__ import annotations

import re

_TOKEN = re.compile(r"[a-z0-9.]+")
STOP = {"the", "a", "an", "of", "to", "and", "is", "be", "for", "in", "on", "with", "when", "that", "verify",
        "test", "should", "must"}


def tokens(text: str) -> set[str]:
    return {t for t in _TOKEN.findall((text or "").lower()) if t not in STOP}


def similarity(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def find_duplicates(items: list[tuple[str, str]], threshold: float = 0.85) -> list[tuple[str, str, float]]:
    """items: (key, signature text). Returns (key, duplicate_of_key, score)."""
    out = []
    for i, (ka, sa) in enumerate(items):
        for kb, sb in items[:i]:
            s = similarity(sa, sb)
            if s >= threshold:
                out.append((ka, kb, round(s, 3)))
                break
    return out
