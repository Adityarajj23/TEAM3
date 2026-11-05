"""Lexicon-based deterministic ambiguity detection."""
from __future__ import annotations

import re

VAGUE_TERMS = {
    "promptly": "No measurable time limit", "as appropriate": "Undefined decision criteria",
    "normally": "Exceptions not specified", "sufficiently": "No measurable threshold",
    "etc": "Open-ended list", "etc.": "Open-ended list", "as needed": "Undefined trigger",
    "reasonable": "Subjective standard", "timely": "No measurable time limit",
    "where possible": "Optional behaviour not bounded", "if applicable": "Applicability undefined",
    "user-friendly": "Subjective quality", "quickly": "No measurable time limit",
    "adequate": "No measurable threshold", "approximately": "Tolerance not specified",
    "and/or": "Logical combination unclear", "some": "Quantity undefined", "various": "Set undefined",
    "should": "Obligation level unclear (use 'must' or 'may')", "tbd": "Value to be determined",
    "periodically": "Frequency undefined", "minimal": "No measurable threshold",
}
_PATTERNS = {t: re.compile(r"(?<![\w-])" + re.escape(t) + r"(?![\w-])", re.IGNORECASE) for t in VAGUE_TERMS}


def detect_ambiguity(text: str) -> list[dict]:
    flags = []
    for term, reason in VAGUE_TERMS.items():
        if term == "etc." and "etc" in [f["term"] for f in flags]:
            continue
        m = _PATTERNS[term].search(text or "")
        if m:
            flags.append({"term": m.group(0), "reason": reason, "offset": m.start(), "source": "lexicon"})
    return flags


_NUMBER = re.compile(r"\d")


def detect_missing_information(text: str) -> list[str]:
    """Heuristic gaps: thresholds/limits mentioned with no number, unspecified actors."""
    gaps = []
    lowered = text.lower()
    for word in ("threshold", "limit", "cap", "maximum", "minimum", "within", "deadline", "cut-off", "cutoff"):
        if word in lowered and not _NUMBER.search(text):
            gaps.append(f"'{word}' is referenced but no numeric value is specified")
            break
    if re.search(r"\b(the system|it)\b", lowered) is None and re.search(r"\b(must|shall)\b", lowered) is None:
        gaps.append("No explicit obligation ('must'/'shall') — expected behaviour may be optional")
    return gaps
