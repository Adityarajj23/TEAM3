"""Deterministic normalised quote verification."""
from __future__ import annotations

import re

_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-"})
_WS = re.compile(r"\s+")
_EDGE = re.compile(r"^[\s\"'.,;:]+|[\s\"'.,;:]+$")


def normalize(text: str) -> str:
    text = (text or "").translate(_QUOTES).lower()
    text = text.replace("…", "...")
    return _WS.sub(" ", text).strip()


def verify_quote(quote: str, source_texts: list[str], min_len: int = 12) -> bool:
    """A quote is verified only if its normalised form occurs verbatim in a cited source clause."""
    q = _EDGE.sub("", normalize(quote))
    if len(q) < min_len:
        return False
    # allow elided quotes "a ... b" — every fragment must appear, in order, in one source
    fragments = [f.strip() for f in q.split("...") if f.strip()]
    for src in source_texts:
        s = normalize(src)
        pos = 0
        ok = True
        for frag in fragments:
            idx = s.find(frag, pos)
            if idx < 0:
                ok = False
                break
            pos = idx + len(frag)
        if ok:
            return True
    # quote may span adjacent clauses
    joined = normalize(" ".join(source_texts))
    return all(f in joined for f in fragments) and len(fragments) == 1 and q in joined
