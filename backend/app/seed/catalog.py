"""Deterministic requirement families for the fictional Northwind Workforce Solutions dataset.

Each family yields requirement text (one sentence per clause) and tests whose expected values are
derived from the requirement (the specification oracle), never from the implementation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class SeedTest:
    title: str
    test_type: str
    priority: str
    clause: int  # 1-based clause index
    module: str  # reference_hcm module or "" for manual tests
    asserts: list[str]  # python lines inside the test function
    expected: str
    data: dict = field(default_factory=dict)
    imports: str = ""

    def script(self, fn_name: str) -> str | None:
        if not self.module:
            return None
        head = f"from reference_hcm import {self.module}\n" + (self.imports + "\n" if self.imports else "")
        body = "\n".join("    " + a for a in self.asserts)
        return f'{head}\n\ndef {fn_name}():\n    """{self.title}"""\n{body}\n'


@dataclass
class SeedRequirement:
    family: str
    project: str
    module: str
    title: str
    clauses: list[str]
    objective: str
    priority: str = "high"
    category: str = "functional"
    tests: list[SeedTest] = field(default_factory=list)
    prior_versions: list[tuple[list[str], str]] = field(default_factory=list)  # (clauses, change summary)
    analysed: bool = True


def _n(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else str(x)


def overtime(project, module, label, t, prio="high") -> SeedRequirement:
    c = [f"Hours worked above {_n(t)} in a payroll week must be paid as overtime for {label}.",
         f"Hours worked at exactly {_n(t)} in a payroll week must not be treated as overtime.",
         "Overtime hours must be reported to two decimal places on the payslip.",
         "Negative weekly hour totals must be rejected as invalid input.",
         "Overtime must be calculated per employee for each payroll week independently."]
    tests = [
        SeedTest(f"{label}: exactly {_n(t)} hours yields no overtime", "boundary", "critical", 2, "payroll",
                 [f"assert payroll.calculate_overtime_hours({t}, threshold={t}) == 0"], "0 overtime hours",
                 {"weekly_hours": t, "threshold": t}),
        SeedTest(f"{label}: one hour above threshold is one overtime hour", "boundary", "critical", 1, "payroll",
                 [f"assert payroll.calculate_overtime_hours({t + 1}, threshold={t}) == 1"], "1 overtime hour",
                 {"weekly_hours": t + 1, "threshold": t}),
        SeedTest(f"{label}: hours below threshold yield no overtime", "negative", "high", 1, "payroll",
                 [f"assert payroll.calculate_overtime_hours({t - 3}, threshold={t}) == 0"], "0 overtime hours",
                 {"weekly_hours": t - 3}),
        SeedTest(f"{label}: fractional overtime reported to two decimals", "functional", "medium", 3, "payroll",
                 [f"assert payroll.calculate_overtime_hours({t + 2.25}, threshold={t}) == 2.25"], "2.25 overtime hours",
                 {"weekly_hours": t + 2.25}),
        SeedTest(f"{label}: negative weekly hours are rejected", "negative", "medium", 4, "payroll",
                 ["with pytest.raises(ValueError):", f"    payroll.calculate_overtime_hours(-1, threshold={t})"],
                 "ValueError raised", {"weekly_hours": -1}, imports="import pytest"),
        SeedTest(f"{label}: long week of {_n(t + 20)} hours yields 20 overtime hours", "regression", "high", 5, "payroll",
                 [f"assert payroll.calculate_overtime_hours({t + 20}, threshold={t}) == 20"], "20 overtime hours",
                 {"weekly_hours": t + 20}),
    ]
    prior = [([c[0].replace(f"above {_n(t)}", f"above {_n(t)} hours (or as appropriate)"), c[2], c[3]],
              "Added explicit boundary and per-week calculation clauses")]
    return SeedRequirement("overtime", project, module, f"Weekly overtime threshold — {label}", c,
                           f"Ensure {label} are paid overtime consistently with the {_n(t)}-hour policy.", prio,
                           "compliance", tests, prior)


def multiplier(project, module, label, m, rate) -> SeedRequirement:
    c = [f"Overtime hours for {label} must be paid at {m} times the base hourly rate.",
         "Regular hours must be paid at the base hourly rate.",
         "Gross pay must be the sum of regular pay and overtime pay.",
         "Gross pay must be expressed in the company currency with two decimal places."]
    reg_pay = rate * 40
    from decimal import ROUND_HALF_UP, Decimal
    gross = (Decimal(str(rate)) * 40 + Decimal(str(rate)) * 5 * Decimal(str(m))).quantize(Decimal("0.01"), ROUND_HALF_UP)
    tests = [
        SeedTest(f"{label}: gross pay with 5 overtime hours", "functional", "critical", 1, "payroll",
                 ["from decimal import Decimal",
                  f"assert payroll.calculate_gross_pay(40, 5, '{rate}', '{m}') == Decimal('{gross}')"],
                 f"{gross}", {"rate": rate, "multiplier": m}),
        SeedTest(f"{label}: regular hours only", "positive", "high", 2, "payroll",
                 ["from decimal import Decimal",
                  f"assert payroll.calculate_gross_pay(40, 0, '{rate}', '{m}') == Decimal('{reg_pay:.2f}')"],
                 f"{reg_pay:.2f}", {"rate": rate}),
        SeedTest(f"{label}: zero hours yields zero pay", "boundary", "medium", 3, "payroll",
                 ["from decimal import Decimal",
                  f"assert payroll.calculate_gross_pay(0, 0, '{rate}', '{m}') == Decimal('0.00')"], "0.00"),
    ]
    return SeedRequirement("multiplier", project, module, f"Overtime multiplier — {label}", c,
                           "Pay overtime at the contracted premium.", "high", "functional", tests)


def rounding(project, module) -> SeedRequirement:
    c = ["Monetary pay amounts must be rounded to two decimal places.",
         "Amounts exactly halfway between two cents must be rounded up, away from zero.",
         "Amounts below the halfway point must be rounded down.",
         "Rounding must be applied once, after all earnings components are summed."]
    tests = [
        SeedTest("Half-cent amount 2.345 rounds up to 2.35", "boundary", "critical", 2, "payroll",
                 ["from decimal import Decimal", "assert payroll.round_pay('2.345') == Decimal('2.35')"], "2.35"),
        SeedTest("Half-cent amount 10.125 rounds up to 10.13", "boundary", "critical", 2, "payroll",
                 ["from decimal import Decimal", "assert payroll.round_pay('10.125') == Decimal('10.13')"], "10.13"),
        SeedTest("Half-cent amount 2.355 rounds up to 2.36", "boundary", "high", 2, "payroll",
                 ["from decimal import Decimal", "assert payroll.round_pay('2.355') == Decimal('2.36')"], "2.36"),
        SeedTest("Amount 7.111 rounds down to 7.11", "functional", "medium", 3, "payroll",
                 ["from decimal import Decimal", "assert payroll.round_pay('7.111') == Decimal('7.11')"], "7.11"),
        SeedTest("Gross pay with half-cent total rounds up once", "compliance", "high", 4, "payroll",
                 ["from decimal import Decimal",
                  "assert payroll.calculate_gross_pay(1, 0, '0.125', '1.5') == Decimal('0.13')"], "0.13"),
    ]
    prior = [([c[0], "Halfway amounts should be rounded normally.", c[2]], "Specified half-up rounding mode")]
    return SeedRequirement("rounding", project, module, "Payroll monetary rounding", c,
                           "Avoid systematic under-payment through rounding.", "critical", "compliance", tests, prior)


def differential(project, module, label, night=10, evening=5) -> SeedRequirement:
    c = [f"Night shift hours worked by {label} must earn a differential of {night} percent of the base rate.",
         f"Evening shift hours must earn a differential of {evening} percent of the base rate.",
         "Day shift hours must not earn a shift differential.",
         "An unrecognised shift code must be rejected."]
    tests = [
        SeedTest(f"{label}: evening differential is {evening}%", "functional", "high", 2, "payroll",
                 ["from decimal import Decimal",
                  f"assert payroll.shift_differential_pay(8, '20', 'evening') == Decimal('{8 * 20 * evening / 100:.2f}')"],
                 f"{8 * 20 * evening / 100:.2f}"),
        SeedTest(f"{label}: night differential is {night}%", "functional", "high", 1, "payroll",
                 ["from decimal import Decimal",
                  f"assert payroll.shift_differential_pay(8, '20', 'night') == Decimal('{8 * 20 * night / 100:.2f}')"],
                 f"{8 * 20 * night / 100:.2f}"),
        SeedTest(f"{label}: day shift earns no differential", "negative", "medium", 3, "payroll",
                 ["from decimal import Decimal", "assert payroll.shift_differential_pay(8, '20', 'day') == Decimal('0.00')"],
                 "0.00"),
        SeedTest(f"{label}: unknown shift code rejected", "negative", "low", 4, "payroll",
                 ["with pytest.raises(ValueError):", "    payroll.shift_differential_pay(8, '20', 'graveyard')"],
                 "ValueError", imports="import pytest"),
    ]
    return SeedRequirement("differential", project, module, f"Shift differentials — {label}", c,
                           "Compensate unsocial hours fairly.", "high", "functional", tests)


def retro(project, module) -> SeedRequirement:
    c = ["Retroactive pay adjustments must equal the rate difference multiplied by the affected hours.",
         "A retroactive rate decrease must produce a negative adjustment that is recovered from the next payslip.",
         "Adjustments must be rounded to two decimal places.",
         "Retroactive adjustments older than 12 months require payroll director approval."]
    tests = [
        SeedTest("Rate increase back-pay for 40 hours", "functional", "high", 1, "payroll",
                 ["from decimal import Decimal", "assert payroll.retroactive_adjustment('20', '22', 40) == Decimal('80.00')"],
                 "80.00"),
        SeedTest("Rate decrease produces negative adjustment", "negative", "high", 2, "payroll",
                 ["from decimal import Decimal", "assert payroll.retroactive_adjustment('22', '20', 10) == Decimal('-20.00')"],
                 "-20.00"),
        SeedTest("Fractional adjustment is rounded", "boundary", "medium", 3, "payroll",
                 ["from decimal import Decimal",
                  "assert payroll.retroactive_adjustment('20.00', '20.333', 3) == Decimal('1.00')"], "1.00"),
        SeedTest("Adjustments older than 12 months route to payroll director", "compliance", "medium", 4, "", [],
                 "Approval task assigned to payroll director"),
    ]
    prior = [(c[:3], "Added approval rule for adjustments older than 12 months")]
    return SeedRequirement("retro", project, module, "Retroactive pay adjustments", c,
                           "Correct historical pay accurately and auditable.", "high", "functional", tests, prior)


def cutoff(project, module, lead=2) -> SeedRequirement:
    c = [f"Timesheets must be submitted no later than 17:00 {lead} days before the payroll period end.",
         "Submissions at exactly 17:00 on the cut-off day must be accepted for the current period.",
         "Submissions after 17:00 on the cut-off day must be processed in the next payroll cycle.",
         "Late submissions should be flagged to the payroll team promptly."]
    tests = [
        SeedTest("Submission exactly at 17:00 on cut-off day is accepted", "boundary", "critical", 2, "payroll",
                 ["from datetime import datetime",
                  f"assert payroll.is_before_cutoff(datetime(2026, 9, {30 - lead}, 17, 0), datetime(2026, 9, 30), {lead}) is True"],
                 "Accepted"),
        SeedTest("Submission at 16:59 on cut-off day is accepted", "boundary", "high", 1, "payroll",
                 ["from datetime import datetime",
                  f"assert payroll.is_before_cutoff(datetime(2026, 9, {30 - lead}, 16, 59), datetime(2026, 9, 30), {lead}) is True"],
                 "Accepted"),
        SeedTest("Submission at 17:01 is deferred to next cycle", "negative", "high", 3, "payroll",
                 ["from datetime import datetime",
                  f"assert payroll.is_before_cutoff(datetime(2026, 9, {30 - lead}, 17, 1), datetime(2026, 9, 30), {lead}) is False"],
                 "Deferred"),
        SeedTest("Cut-off timestamp is 17:00 on the lead day", "functional", "medium", 1, "payroll",
                 ["from datetime import datetime",
                  f"assert payroll.payroll_cutoff(datetime(2026, 9, 30), {lead}) == datetime(2026, 9, {30 - lead}, 17, 0)"],
                 f"2026-09-{30 - lead} 17:00"),
        SeedTest("Late submission notification reaches payroll team", "integration", "low", 4, "", [],
                 "Notification raised"),
    ]
    return SeedRequirement("cutoff", project, module, f"Payroll timesheet cut-off — {lead}-day lead", c,
                           "Close payroll on schedule without losing valid submissions.", "critical", "compliance", tests)


def holiday(project, module, label, mult="2.0") -> SeedRequirement:
    c = [f"Hours worked on a designated public holiday by {label} must be paid at {mult} times the base rate.",
         "The holiday calendar must be maintained per work location.",
         "Holiday premium must not be combined with the overtime premium for the same hour."]
    tests = [
        SeedTest(f"{label}: 8 holiday hours at base 20", "functional", "high", 1, "payroll",
                 ["from decimal import Decimal",
                  f"assert payroll.holiday_pay(8, '20', '{mult}') == Decimal('{8 * 20 * float(mult):.2f}')"],
                 f"{8 * 20 * float(mult):.2f}"),
        SeedTest(f"{label}: zero holiday hours", "boundary", "low", 1, "payroll",
                 ["from decimal import Decimal", f"assert payroll.holiday_pay(0, '20', '{mult}') == Decimal('0.00')"], "0.00"),
        SeedTest(f"{label}: location-specific calendar applied", "integration", "medium", 2, "", [],
                 "Calendar for employee location used"),
        SeedTest(f"{label}: holiday and overtime premiums not stacked", "negative", "high", 3, "", [],
                 "Single highest premium applied"),
    ]
    return SeedRequirement("holiday", project, module, f"Public holiday premium — {label}", c,
                           "Apply holiday pay consistently across locations.", "medium", "functional", tests)


def punches(project, module) -> SeedRequirement:
    c = ["Every clock-in must be paired with the next clock-out recorded for the same employee.",
         "A clock-in without a matching clock-out must be flagged as a missed punch.",
         "A clock-out without a preceding clock-in must be flagged as a missed punch.",
         "Worked hours must be calculated only from complete punch pairs.",
         "Punches must be evaluated in chronological order regardless of the order received."]
    head = ["from datetime import datetime"]
    tests = [
        SeedTest("Complete IN/OUT pair has no missed punch", "positive", "high", 1, "attendance",
                 head + ["p = [('IN', datetime(2026, 9, 1, 9)), ('OUT', datetime(2026, 9, 1, 17))]",
                         "assert attendance.has_missed_punch(p) is False"], "No missed punch"),
        SeedTest("Clock-in without clock-out is flagged", "negative", "critical", 2, "attendance",
                 head + ["p = [('IN', datetime(2026, 9, 1, 9))]", "assert attendance.has_missed_punch(p) is True"],
                 "Missed punch flagged"),
        SeedTest("Clock-out without clock-in is flagged", "negative", "high", 3, "attendance",
                 head + ["p = [('OUT', datetime(2026, 9, 1, 17))]", "assert attendance.has_missed_punch(p) is True"],
                 "Missed punch flagged"),
        SeedTest("Worked hours only from complete pairs", "functional", "high", 4, "attendance",
                 head + ["p = [('IN', datetime(2026, 9, 1, 9)), ('OUT', datetime(2026, 9, 1, 13)),",
                         "     ('IN', datetime(2026, 9, 1, 14))]", "assert attendance.worked_hours(p) == 4.0"], "4.0 hours"),
        SeedTest("Out-of-order punches are sorted chronologically", "regression", "medium", 5, "attendance",
                 head + ["p = [('OUT', datetime(2026, 9, 1, 17)), ('IN', datetime(2026, 9, 1, 9))]",
                         "assert attendance.worked_hours(p) == 8.0"], "8.0 hours"),
    ]
    prior = [(c[:3], "Clarified worked-hours calculation and ordering")]
    return SeedRequirement("punches", project, module, "Punch pairing and missed-punch detection", c,
                           "Produce accurate worked time from raw clock events.", "critical", "functional", tests, prior)


def meal_break(project, module, label, shift=6, minutes=30) -> SeedRequirement:
    c = [f"{label} working shifts longer than {shift} hours must take a meal break of at least {minutes} minutes.",
         f"A meal break of exactly {minutes} minutes must be treated as compliant.",
         f"Shifts of {shift} hours or less do not require a meal break.",
         "Non-compliant shifts must be reported to the site supervisor as appropriate."]
    tests = [
        SeedTest(f"{label}: exactly {minutes}-minute break is compliant", "boundary", "critical", 2, "attendance",
                 [f"assert attendance.meal_break_compliant({shift + 2}, {minutes}, {shift}, {minutes}) is True"],
                 "Compliant"),
        SeedTest(f"{label}: {minutes - 1}-minute break is non-compliant", "boundary", "high", 1, "attendance",
                 [f"assert attendance.meal_break_compliant({shift + 2}, {minutes - 1}, {shift}, {minutes}) is False"],
                 "Non-compliant"),
        SeedTest(f"{label}: {shift}-hour shift needs no break", "negative", "medium", 3, "attendance",
                 [f"assert attendance.meal_break_compliant({shift}, 0, {shift}, {minutes}) is True"], "Compliant"),
        SeedTest(f"{label}: long break is compliant", "positive", "low", 1, "attendance",
                 [f"assert attendance.meal_break_compliant({shift + 4}, {minutes + 15}, {shift}, {minutes}) is True"],
                 "Compliant"),
    ]
    return SeedRequirement("meal_break", project, module, f"Meal-break compliance — {label}", c,
                           "Meet statutory rest-break obligations.", "critical", "compliance", tests)


def accrual(project, module, label, rate, cap) -> SeedRequirement:
    c = [f"{label} must accrue {rate} days of annual leave per completed month of service.",
         f"Annual accrual must not exceed {cap} days in a leave year.",
         "Partial months must not accrue leave.",
         "A negative service duration must be rejected."]
    tests = [
        SeedTest(f"{label}: 4 months accrue {4 * rate} days", "functional", "high", 1, "leave",
                 [f"assert leave.accrue_leave(4, {rate}, {cap}) == {round(4 * rate, 2)}"], f"{4 * rate} days"),
        SeedTest(f"{label}: accrual capped at {cap} days", "boundary", "high", 2, "leave",
                 [f"assert leave.accrue_leave(24, {rate}, {cap}) == {cap}"], f"{cap} days"),
        SeedTest(f"{label}: zero months accrue nothing", "boundary", "medium", 3, "leave",
                 [f"assert leave.accrue_leave(0, {rate}, {cap}) == 0"], "0 days"),
        SeedTest(f"{label}: negative months rejected", "negative", "low", 4, "leave",
                 ["with pytest.raises(ValueError):", f"    leave.accrue_leave(-1, {rate}, {cap})"], "ValueError",
                 imports="import pytest"),
    ]
    prior = [([c[0], "Annual accrual is capped.", c[3]], "Specified numeric annual cap")]
    return SeedRequirement("accrual", project, module, f"Leave accrual — {label}", c,
                           "Accrue leave entitlement accurately each month.", "high", "functional", tests, prior)


def carry(project, module, label, cap) -> SeedRequirement:
    c = [f"Unused annual leave for {label} may be carried forward into the next leave year.",
         f"The carried-forward balance must not exceed {cap} days.",
         "Any balance above the carry-forward cap must be forfeited.",
         "A negative leave balance must be rejected during year-end processing."]
    tests = [
        SeedTest(f"{label}: balance above cap is limited to {cap}", "boundary", "critical", 2, "leave",
                 [f"assert leave.carry_forward({cap + 2}, cap={cap}) == {cap}"], f"{cap} days"),
        SeedTest(f"{label}: balance below cap carried in full", "positive", "high", 1, "leave",
                 [f"assert leave.carry_forward({cap - 3}, cap={cap}) == {cap - 3}"], f"{cap - 3} days"),
        SeedTest(f"{label}: balance equal to cap is carried in full", "boundary", "high", 2, "leave",
                 [f"assert leave.carry_forward({cap}, cap={cap}) == {cap}"], f"{cap} days"),
        SeedTest(f"{label}: excess balance forfeited", "functional", "medium", 3, "leave",
                 [f"assert {cap + 9} - leave.carry_forward({cap + 9}, cap={cap}) == 9"], "9 days forfeited"),
        SeedTest(f"{label}: negative balance rejected", "negative", "low", 4, "leave",
                 ["with pytest.raises(ValueError):", f"    leave.carry_forward(-2, cap={cap})"], "ValueError",
                 imports="import pytest"),
    ]
    return SeedRequirement("carry", project, module, f"Leave carry-forward cap — {label}", c,
                           "Limit leave liability carried between years.", "high", "compliance", tests)


def payout(project, module, label: str = "all employees") -> SeedRequirement:
    c = ["On termination the remaining leave balance must be paid out at the employee's daily rate.",
         "The termination payout must be rounded to two decimal places.",
         "A zero leave balance must produce no payout line on the final payslip."]
    tests = [
        SeedTest("Payout of 5.5 days at 180.00", "functional", "high", 1, "leave",
                 ["from decimal import Decimal", "assert leave.termination_payout(5.5, '180.00') == Decimal('990.00')"],
                 "990.00"),
        SeedTest("Payout rounding of fractional rate", "boundary", "medium", 2, "leave",
                 ["from decimal import Decimal", "assert leave.termination_payout(3, '33.335') == Decimal('100.01')"],
                 "100.01"),
        SeedTest("Zero balance produces zero payout", "boundary", "low", 3, "leave",
                 ["from decimal import Decimal", "assert leave.termination_payout(0, '180') == Decimal('0.00')"], "0.00"),
    ]
    return SeedRequirement("payout", project, module, f"Termination leave payout — {label}", c,
                           "Settle leave entitlement correctly on exit.", "high", "compliance", tests)


def approvals(project, module, role, limit) -> SeedRequirement:
    c = [f"A {role} may approve pay and expense adjustments up to and including {limit}.",
         f"Adjustments above {limit} must be escalated to the next approval level.",
         "Negative adjustment amounts must not be approvable.",
         "Roles without an approval limit must not approve adjustments."]
    tests = [
        SeedTest(f"{role.title()} can approve exactly {limit}", "boundary", "critical", 1, "approvals",
                 [f"assert approvals.can_approve('{role}', {limit}) is True"], "Approved"),
        SeedTest(f"{role.title()} can approve below limit", "positive", "high", 1, "approvals",
                 [f"assert approvals.can_approve('{role}', {limit - 1}) is True"], "Approved"),
        SeedTest(f"{role.title()} cannot approve above limit", "negative", "critical", 2, "approvals",
                 [f"assert approvals.can_approve('{role}', {limit + 1}) is False"], "Escalated"),
        SeedTest(f"{role.title()} cannot approve negative amounts", "security", "medium", 3, "approvals",
                 [f"assert approvals.can_approve('{role}', -10) is False"], "Rejected"),
        SeedTest("Employee role cannot approve adjustments", "security", "high", 4, "approvals",
                 ["assert approvals.can_approve('employee', 10) is False"], "Rejected"),
    ]
    return SeedRequirement("approvals", project, module, f"Approval limit — {role}", c,
                           "Enforce delegated financial authority.", "critical", "security", tests)


def permissions(project, module) -> SeedRequirement:
    c = ["Only payroll administrators must be permitted to run payroll.",
         "Managers must be permitted to approve leave and timesheets for their reports.",
         "Employees must not be permitted to edit pay rates.",
         "Unknown roles must be denied every permission."]
    tests = [
        SeedTest("Payroll admin can run payroll", "security", "critical", 1, "approvals",
                 ["assert approvals.has_permission('payroll_admin', 'run_payroll') is True"], "Allowed"),
        SeedTest("Manager cannot run payroll", "security", "critical", 1, "approvals",
                 ["assert approvals.has_permission('manager', 'run_payroll') is False"], "Denied"),
        SeedTest("Manager can approve timesheets", "positive", "high", 2, "approvals",
                 ["assert approvals.has_permission('manager', 'approve_timesheet') is True"], "Allowed"),
        SeedTest("Employee cannot edit pay rates", "security", "critical", 3, "approvals",
                 ["assert approvals.has_permission('employee', 'edit_pay_rates') is False"], "Denied"),
        SeedTest("Unknown role denied", "security", "high", 4, "approvals",
                 ["assert approvals.has_permission('contractor_admin', 'submit_leave') is False"], "Denied"),
    ]
    return SeedRequirement("permissions", project, module, "Role-based HCM permissions", c,
                           "Least-privilege access to sensitive HCM actions.", "critical", "security", tests)


def eligibility(project, module, label, waiting=90, pt_hours=30) -> SeedRequirement:
    c = [f"Full-time employees in {label} become eligible for benefits after {waiting} days of continuous service.",
         f"Part-time employees are eligible after {waiting} days only if they work at least {pt_hours} hours per week.",
         "Contractors must never be eligible for company benefits.",
         "Seasonal workers must not be eligible for company benefits.",
         "Employees with fewer than the waiting-period days must not be eligible."]
    w, h = waiting, pt_hours
    tests = [
        SeedTest(f"{label}: full-time at {w} days eligible", "boundary", "high", 1, "eligibility",
                 [f"assert eligibility.benefits_eligible({w}, 'full_time', 40, {w}, {h}) is True"], "Eligible"),
        SeedTest(f"{label}: full-time at {w - 1} days not eligible", "boundary", "high", 5, "eligibility",
                 [f"assert eligibility.benefits_eligible({w - 1}, 'full_time', 40, {w}, {h}) is False"], "Not eligible"),
        SeedTest(f"{label}: part-time {h}h/week eligible", "boundary", "high", 2, "eligibility",
                 [f"assert eligibility.benefits_eligible({w + 10}, 'part_time', {h}, {w}, {h}) is True"], "Eligible"),
        SeedTest(f"{label}: part-time {h - 1}h/week not eligible", "negative", "high", 2, "eligibility",
                 [f"assert eligibility.benefits_eligible({w + 10}, 'part_time', {h - 1}, {w}, {h}) is False"],
                 "Not eligible"),
        SeedTest(f"{label}: contractor never eligible", "compliance", "critical", 3, "eligibility",
                 [f"assert eligibility.benefits_eligible(400, 'contractor', 40, {w}, {h}) is False"], "Not eligible"),
        SeedTest(f"{label}: seasonal worker not eligible", "compliance", "medium", 4, "eligibility",
                 [f"assert eligibility.benefits_eligible(400, 'seasonal', 40, {w}, {h}) is False"], "Not eligible"),
        SeedTest(f"{label}: part-time below waiting period not eligible", "negative", "medium", 5, "eligibility",
                 [f"assert eligibility.benefits_eligible({w - 1}, 'part_time', {h + 5}, {w}, {h}) is False"],
                 "Not eligible"),
    ]
    prior = [([c[0], c[1], "Contractors and seasonal workers are generally excluded, etc."],
              "Made contractor and seasonal exclusions explicit")]
    return SeedRequirement("eligibility", project, module, f"Benefits eligibility — {label}", c,
                           "Offer benefits only to eligible populations.", "critical", "compliance", tests, prior)


def manual(project, module, title, clauses, objective, test_titles, prio="medium", category="functional",
           ttype="functional") -> SeedRequirement:
    tests = [SeedTest(tt, ttype if i else "functional", prio, min(i + 1, len(clauses)), "", [], "As stated")
             for i, tt in enumerate(test_titles)]
    return SeedRequirement("manual", project, module, title, clauses, objective, prio, category, tests)


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:60]


def build_catalog() -> list[SeedRequirement]:
    R: list[SeedRequirement] = []
    # ---------------- PAY: Payroll Management ----------------
    R += [overtime("PAY", "OVT", "hourly office staff", 40), overtime("PAY", "OVT", "warehouse staff (Site B)", 48),
          overtime("PAY", "OVT", "retail associates", 44, "medium"),
          multiplier("PAY", "OVT", "hourly office staff", 1.5, 18.0), multiplier("PAY", "OVT", "night drivers", 2.0, 21.0),
          differential("PAY", "OVT", "distribution centre staff"), rounding("PAY", "CMP"), retro("PAY", "ADJ"),
          cutoff("PAY", "ADJ", 2), cutoff("PAY", "ADJ", 3), holiday("PAY", "CMP", "salaried staff"),
          payout("PAY", "ADJ", "payroll final settlement")]
    R += [manual("PAY", "CMP", "Payslip delivery and retention",
                 ["Payslips must be available in the employee portal on the pay date.",
                  "Payslips must be retained for at least seven years.",
                  "Employees must be able to download payslips as PDF documents."],
                 "Meet payslip access and retention obligations.",
                 ["Payslip visible on pay date", "Payslip retention policy enforced", "Payslip PDF download"],
                 "high", "compliance", "compliance"),
          manual("PAY", "CMP", "Payroll audit trail",
                 ["Every change to an employee pay rate must be recorded with the user, timestamp and reason.",
                  "Audit records must not be editable by any role.",
                  "Payroll administrators must be able to export the audit trail for a date range."],
                 "Provide a defensible record of pay changes.",
                 ["Pay rate change captured in audit", "Audit records immutable", "Audit export by date range"],
                 "high", "security", "security")]
    # ---------------- TNA: Time and Attendance ----------------
    R += [punches("TNA", "PCH"), meal_break("TNA", "BRK", "Hourly employees"),
          meal_break("TNA", "BRK", "Warehouse employees", 5, 30), meal_break("TNA", "BRK", "Drivers", 8, 45),
          overtime("TNA", "PCH", "attendance-tracked staff", 40, "medium"),
          manual("TNA", "PCH", "Clock-in rounding window",
                 ["Clock-in times must be rounded to the nearest 15 minutes.",
                  "Rounding must be neutral over a pay period and must not systematically favour the employer.",
                  "Supervisors should be able to review rounded punches."],
                 "Apply fair and neutral time rounding.",
                 ["Clock-in rounding to nearest quarter hour", "Rounding neutrality over a period",
                  "Supervisor review of rounded punches"], "high", "compliance", "compliance"),
          manual("TNA", "BRK", "Rest period between shifts",
                 ["Employees must have at least 11 consecutive hours of rest between shifts.",
                  "Scheduling a shift that breaks the rest period must require manager override.",
                  "Overrides must be recorded with a reason."],
                 "Protect employee rest.",
                 ["Rest period validation", "Manager override required", "Override reason recorded"],
                 "high", "compliance", "compliance"),
          manual("TNA", "PCH", "Geofenced mobile clock-in",
                 ["Mobile clock-in must only be accepted within the configured site geofence.",
                  "Clock-in attempts outside the geofence must be rejected with an explanatory message.",
                  "Location data must be retained only for the duration of the punch audit window."],
                 "Prevent remote time fraud.",
                 ["Clock-in inside geofence accepted", "Clock-in outside geofence rejected",
                  "Location data retention"], "medium", "security", "security")]
    # ---------------- LVE: Employee Leave Management ----------------
    R += [accrual("LVE", "ACR", "Full-time employees", 1.5, 18), accrual("LVE", "ACR", "Part-time employees", 0.75, 9),
          accrual("LVE", "ACR", "Senior staff (10+ years)", 2.0, 24),
          carry("LVE", "CFW", "head-office employees", 10), carry("LVE", "CFW", "field employees", 20),
          carry("LVE", "CFW", "part-time employees", 5), payout("LVE", "CFW", "leave balance settlement"),
          manual("LVE", "ACR", "Leave request approval workflow",
                 ["Leave requests must be approved by the employee's direct manager.",
                  "Managers must respond to leave requests promptly.",
                  "Approved leave must be deducted from the balance when the leave is taken."],
                 "Provide a clear leave approval path.",
                 ["Leave request routed to direct manager", "Manager response tracked",
                  "Balance deducted on leave date"], "medium"),
          manual("LVE", "ACR", "Sick leave certification",
                 ["Sick leave longer than 3 consecutive days must require a medical certificate.",
                  "Certificates must be visible only to HR and the employee.",
                  "Missing certificates must be followed up as needed."],
                 "Balance privacy with absence control.",
                 ["Certificate required after 3 days", "Certificate visibility restricted",
                  "Missing certificate follow-up"], "high", "security", "security")]
    # ---------------- WFS: Workforce Scheduling ----------------
    R += [approvals("WFS", "APR", "manager", 5000), approvals("WFS", "APR", "director", 25000), permissions("WFS", "APR"),
          holiday("WFS", "HOL", "rostered shift workers"), holiday("WFS", "HOL", "contact-centre agents", "2.5"),
          differential("WFS", "SHF", "rostered shift workers"),
          manual("WFS", "SHF", "Shift swap requests",
                 ["Employees may request to swap shifts with a qualified colleague.",
                  "Shift swaps must be approved by the scheduling manager before they take effect.",
                  "A swap must not create a rest-period violation for either employee."],
                 "Allow flexibility without compliance risk.",
                 ["Shift swap request created", "Swap requires manager approval", "Swap rejected on rest violation"]),
          manual("WFS", "SHF", "Minimum staffing levels",
                 ["Each site must define a minimum number of staff per shift.",
                  "The schedule must warn when a shift falls below the minimum staffing level.",
                  "Publishing a schedule below minimum staffing must require director approval."],
                 "Maintain safe staffing.",
                 ["Minimum staffing configured", "Understaffing warning", "Director approval to publish"], "high"),
          manual("WFS", "HOL", "Holiday calendar maintenance",
                 ["Holiday calendars must be maintained per country and region.",
                  "Calendar changes must take effect only for future pay periods.",
                  "Calendar administrators must be notified of conflicting holiday dates."],
                 "Keep holiday data accurate.",
                 ["Regional calendar applied", "Future-only calendar changes", "Conflict notification"])]
    # ---------------- BEN: Benefits and Eligibility ----------------
    R += [eligibility("BEN", "ELG", "the United Kingdom entity"), eligibility("BEN", "ELG", "the India entity", 60, 30),
          eligibility("BEN", "ELG", "the United States entity", 90, 25),
          manual("BEN", "ENR", "Open enrolment window",
                 ["Open enrolment must run for 30 days each benefit year.",
                  "Employees must not change benefit elections outside open enrolment without a qualifying life event.",
                  "Confirmation of elections must be sent to the employee."],
                 "Control benefit election changes.",
                 ["Open enrolment window enforced", "Mid-year change requires life event", "Election confirmation sent"],
                 "high", "compliance", "compliance"),
          manual("BEN", "ENR", "Dependent verification",
                 ["Dependents added to a medical plan must be verified within 60 days.",
                  "Unverified dependents must be removed from coverage after the verification deadline.",
                  "Verification documents must be stored securely."],
                 "Prevent ineligible dependent coverage.",
                 ["Dependent verification deadline", "Unverified dependent removed", "Secure document storage"],
                 "medium", "compliance", "compliance"),
          manual("BEN", "ELG", "Benefits termination",
                 ["Benefits must end on the last day of the month in which employment terminates.",
                  "Terminated employees must receive continuation-of-coverage information.",
                  "Benefit deductions must stop with the final payroll."],
                 "Close out benefits cleanly at exit.",
                 ["Benefits end at month end", "Continuation information sent", "Deductions stop on final payroll"])]
    # ---------------- additional regional variants ----------------
    R += [overtime("PAY", "OVT", "contact-centre agents", 37.5), multiplier("PAY", "OVT", "holiday cover staff", 1.75, 19.5),
          differential("PAY", "OVT", "security officers", 12, 6), cutoff("PAY", "ADJ", 1),
          overtime("TNA", "PCH", "night drivers", 45), meal_break("TNA", "BRK", "Contact-centre staff", 6, 20),
          accrual("LVE", "ACR", "Fixed-term employees", 1.25, 15), carry("LVE", "CFW", "contact-centre employees", 8),
          carry("LVE", "CFW", "senior staff", 15), approvals("WFS", "APR", "vp", 100000),
          holiday("WFS", "HOL", "warehouse shift workers", "3.0"), differential("WFS", "SHF", "clinic staff", 15, 7),
          eligibility("BEN", "ELG", "the Germany entity", 180, 20), eligibility("BEN", "ELG", "the Singapore entity", 30, 25)]
    # ---------------- ambiguous / conflicting / incomplete requirements ----------------
    R += [manual("PAY", "OVT", "Supervisor overtime eligibility",
                 ["Supervisors must be paid overtime for hours worked above 40 in a payroll week.",
                  "Supervisors must not be paid overtime under any circumstances.",
                  "Exceptions are handled as appropriate by HR."],
                 "Clarify supervisor overtime treatment.", ["Supervisor overtime rule clarified with HR"], "high"),
          manual("LVE", "CFW", "Carry-forward for long-service staff",
                 ["Long-service staff may carry forward additional leave.",
                  "The additional carry-forward cap applies to staff with sufficient tenure.",
                  "Requests should be processed in a timely manner."],
                 "Reward long service.", ["Long-service carry-forward behaviour reviewed"], "medium"),
          manual("TNA", "BRK", "Paid break treatment",
                 ["Short breaks of up to 15 minutes must be paid.",
                  "All breaks must be unpaid.",
                  "Break rules normally follow the site agreement."],
                 "Clarify break pay.", ["Break pay rules confirmed"], "medium")]
    # ---------------- unanalysed requirements (fresh intake) ----------------
    fresh = [
        ("PAY", "OVT", "Daily overtime for California-style sites",
         ["Hours worked above 8 in a single workday must be paid as overtime.",
          "Hours worked above 12 in a single workday must be paid at double time.",
          "Daily and weekly overtime must not be paid twice for the same hour."]),
        ("TNA", "BRK", "Second meal break for extended shifts",
         ["Employees working more than 10 hours must take a second meal break of at least 30 minutes.",
          "The second meal break must start before the end of the tenth hour.",
          "Supervisors should be alerted promptly when a second break is missed."]),
        ("LVE", "CFW", "Carry-forward expiry",
         ["Carried-forward leave must be used within 3 months of the new leave year.",
          "Unused carried-forward leave must expire at the end of the third month.",
          "Employees must be reminded of expiring leave 14 days before expiry."]),
        ("WFS", "APR", "Vice-president approval limit",
         ["A vice-president may approve adjustments up to and including 100000.",
          "Adjustments above 100000 must be approved by the chief financial officer.",
          "Approvals must be recorded in the audit trail."]),
        ("BEN", "ELG", "Benefits eligibility for rehired employees",
         ["Employees rehired within 30 days of termination must retain prior benefits eligibility.",
          "Employees rehired after 30 days must serve a new waiting period.",
          "Prior service credit must be applied as appropriate."]),
    ]
    for proj, mod, title, cl in fresh:
        R.append(SeedRequirement("fresh", proj, mod, title, cl, "Newly received business requirement.", "high",
                                 "functional", [], [], analysed=False))
    return R
