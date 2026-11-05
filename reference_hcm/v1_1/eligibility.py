"""Benefits eligibility rules — v1.1 fix candidate."""
from __future__ import annotations

EMPLOYMENT_TYPES = ("full_time", "part_time", "contractor", "seasonal")


def benefits_eligible(tenure_days: int, employment_type: str, weekly_hours: float = 40,
                      waiting_days: int = 90, part_time_min_hours: float = 30) -> bool:
    if employment_type not in EMPLOYMENT_TYPES:
        raise ValueError(f"unknown employment type {employment_type!r}")
    if employment_type in ("contractor", "seasonal"):
        return False
    if tenure_days < waiting_days:
        return False
    if employment_type == "part_time":
        return weekly_hours >= part_time_min_hours
    return True
