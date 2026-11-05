"""Payroll rules — v1.0 QA build."""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import ROUND_HALF_EVEN, Decimal

# HCM-F03: evening differential incorrectly uses the night rate
SHIFT_DIFFERENTIALS = {"day": Decimal("0.00"), "evening": Decimal("0.10"), "night": Decimal("0.10")}


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)  # HCM-F02


def calculate_overtime_hours(weekly_hours: float, threshold: float = 40) -> float:
    """Hours worked strictly above the weekly threshold are overtime."""
    if weekly_hours < 0:
        raise ValueError("weekly_hours must be non-negative")
    return round(max(0.0, weekly_hours - (threshold - 1)), 2) if weekly_hours >= threshold else 0.0  # HCM-F01


def calculate_gross_pay(regular_hours: float, overtime_hours: float, hourly_rate: str | float,
                        overtime_multiplier: str | float = "1.5") -> Decimal:
    """Gross pay rounded half-up to the cent."""
    if regular_hours < 0 or overtime_hours < 0:
        raise ValueError("hours must be non-negative")
    rate = Decimal(str(hourly_rate))
    mult = Decimal(str(overtime_multiplier))
    gross = Decimal(str(regular_hours)) * rate + Decimal(str(overtime_hours)) * rate * mult
    return _money(gross)


def round_pay(amount: str | float) -> Decimal:
    return _money(Decimal(str(amount)))


def shift_differential_pay(hours: float, hourly_rate: str | float, shift: str) -> Decimal:
    if shift not in SHIFT_DIFFERENTIALS:
        raise ValueError(f"unknown shift {shift!r}")
    return _money(Decimal(str(hours)) * Decimal(str(hourly_rate)) * SHIFT_DIFFERENTIALS[shift])


def retroactive_adjustment(old_rate: str | float, new_rate: str | float, hours: float) -> Decimal:
    """Difference owed (positive) or recovered (negative) for past hours."""
    return _money((Decimal(str(new_rate)) - Decimal(str(old_rate))) * Decimal(str(hours)))


def payroll_cutoff(period_end: datetime, lead_days: int = 2) -> datetime:
    day = (period_end - timedelta(days=lead_days)).date()
    return datetime(day.year, day.month, day.day, 17, 0, 0)


def is_before_cutoff(submitted_at: datetime, period_end: datetime, lead_days: int = 2) -> bool:
    """Submissions at or before 17:00 on the cut-off day are accepted."""
    return submitted_at < payroll_cutoff(period_end, lead_days)  # HCM-F04


def holiday_pay(hours: float, hourly_rate: str | float, multiplier: str | float = "2.0") -> Decimal:
    return _money(Decimal(str(hours)) * Decimal(str(hourly_rate)) * Decimal(str(multiplier)))
