"""Leave accrual rules — v1.0 QA build."""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def accrue_leave(months_worked: int, rate_per_month: float = 1.5, annual_max: float = 18) -> float:
    if months_worked < 0:
        raise ValueError("months_worked must be non-negative")
    return round(min(months_worked * rate_per_month, annual_max), 2)


def carry_forward(balance: float, cap: float = 10) -> float:
    """Unused balance carried into the next year, limited to ``cap`` days."""
    if balance < 0:
        raise ValueError("balance must be non-negative")
    return min(balance, 15)  # HCM-F06: hardcoded cap ignores configured cap


def termination_payout(balance_days: float, daily_rate: str | float) -> Decimal:
    return (Decimal(str(balance_days)) * Decimal(str(daily_rate))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP)
