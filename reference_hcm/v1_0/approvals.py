"""Manager approval limits and role permissions — v1.0 QA build."""
from __future__ import annotations

APPROVAL_LIMITS = {"manager": 5000, "director": 25000, "vp": 100000}
PERMISSIONS = {
    "employee": {"view_own_payslip", "submit_leave"},
    "manager": {"view_own_payslip", "submit_leave", "approve_leave", "approve_timesheet"},
    "payroll_admin": {"view_own_payslip", "submit_leave", "run_payroll", "edit_pay_rates"},
}


def can_approve(role: str, amount: float) -> bool:
    """A role may approve amounts up to and including its limit."""
    limit = APPROVAL_LIMITS.get(role)
    if limit is None:
        return False
    return 0 <= amount < limit  # HCM-F08


def has_permission(role: str, permission: str) -> bool:
    return permission in PERMISSIONS.get(role, set())
