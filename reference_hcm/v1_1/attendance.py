"""Time and attendance rules — v1.1 fix candidate."""
from __future__ import annotations

from datetime import datetime


def pair_punches(punches: list[tuple[str, datetime]]) -> dict:
    """Pair IN/OUT punches in chronological order.

    Returns {"pairs": [(in, out), ...], "missed": [(type, ts), ...]}.
    """
    ordered = sorted(punches, key=lambda p: p[1])
    pairs: list[tuple[datetime, datetime]] = []
    missed: list[tuple[str, datetime]] = []
    open_in: datetime | None = None
    for kind, ts in ordered:
        if kind not in ("IN", "OUT"):
            raise ValueError(f"unknown punch type {kind!r}")
        if kind == "IN":
            if open_in is not None:
                missed.append(("IN", open_in))
            open_in = ts
        else:
            if open_in is None:
                missed.append(("OUT", ts))
            else:
                pairs.append((open_in, ts))
                open_in = None
    if open_in is not None:
        missed.append(("IN", open_in))
    return {"pairs": pairs, "missed": missed}


def has_missed_punch(punches: list[tuple[str, datetime]]) -> bool:
    return bool(pair_punches(punches)["missed"])


def worked_hours(punches: list[tuple[str, datetime]]) -> float:
    total = sum((o - i).total_seconds() for i, o in pair_punches(punches)["pairs"])
    return round(total / 3600, 2)


def meal_break_compliant(shift_hours: float, break_minutes: int, min_shift_hours: float = 6,
                         required_minutes: int = 30) -> bool:
    """Shifts longer than ``min_shift_hours`` need a break of at least ``required_minutes``."""
    if shift_hours <= min_shift_hours:
        return True
    return break_minutes >= required_minutes
