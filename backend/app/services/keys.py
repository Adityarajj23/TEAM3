"""Deterministic human-readable identifiers."""
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session


def next_key(db: Session, model, prefix: str, width: int = 4) -> str:
    """Next sequential key like PREFIX-0007, based on existing keys with that prefix."""
    rows = db.execute(select(model.key).where(model.key.like(prefix + "-%"))).scalars().all()
    nums = [int(m.group(1)) for k in rows if (m := re.match(re.escape(prefix) + r"-(\d+)$", k))]
    return f"{prefix}-{(max(nums) + 1 if nums else 1):0{width}d}"
