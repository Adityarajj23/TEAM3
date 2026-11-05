"""Clause coverage calculation (deterministic)."""
from __future__ import annotations


def clause_coverage(clause_keys: list[str], covered_lists: list[list[str]]) -> dict:
    covered = set()
    for lst in covered_lists:
        covered.update(lst)
    keys = list(clause_keys)
    hit = [k for k in keys if k in covered]
    missing = [k for k in keys if k not in covered]
    orphan_refs = sorted(covered - set(keys))
    pct = round(100.0 * len(hit) / len(keys), 1) if keys else 0.0
    return {"total": len(keys), "covered": len(hit), "uncovered": missing, "coverage_pct": pct,
            "unknown_references": orphan_refs}
