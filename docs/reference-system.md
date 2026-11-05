# Reference HCM Engine

`reference_hcm/` is a small, deterministic, fictional HCM library used as the system under test. Generated and seeded
pytest scripts import only its public API:

```python
from reference_hcm import payroll, attendance, leave, eligibility, approvals
```

The build is selected by `REFERENCE_HCM_VERSION` (`1.0` or `1.1`), which the sandbox sets from the execution
environment. Each project has two environments: **QA — Reference HCM 1.0** (default) and **Fix candidate —
Reference HCM 1.1**.

| Module | Functions |
|---|---|
| `payroll` | `calculate_overtime_hours`, `calculate_gross_pay`, `round_pay`, `shift_differential_pay`, `retroactive_adjustment`, `payroll_cutoff`, `is_before_cutoff`, `holiday_pay` |
| `attendance` | `pair_punches`, `has_missed_punch`, `worked_hours`, `meal_break_compliant` |
| `leave` | `accrue_leave`, `carry_forward`, `termination_payout` |
| `eligibility` | `benefits_eligible` |
| `approvals` | `can_approve`, `has_permission` |

## Deliberate faults in 1.0 (fixed in 1.1)

These are real code differences between `reference_hcm/v1_0` and `reference_hcm/v1_1` (`diff -r` shows exactly
these lines plus module docstrings), not fabricated outcomes.

| ID | Location | 1.0 behaviour | 1.1 behaviour | Detected by seeded tests |
|---|---|---|---|---|
| HCM-F01 | `payroll.calculate_overtime_hours` | Off-by-one: counts hours from `threshold - 1` once the threshold is reached (40 h → 1 h OT) | Only hours strictly above the threshold | Yes (all overtime requirements) |
| HCM-F02 | `payroll._money` / `round_pay` / `calculate_gross_pay` | `ROUND_HALF_EVEN` (2.345 → 2.34) | `ROUND_HALF_UP` (2.345 → 2.35) | Yes |
| HCM-F03 | `payroll.SHIFT_DIFFERENTIALS` | Evening differential uses the night rate (10%) | Evening 5% | Yes |
| HCM-F04 | `payroll.is_before_cutoff` | Exclusive boundary: 17:00 on the cut-off day is rejected | Inclusive (`<=`) | Yes |
| HCM-F05 | `attendance.meal_break_compliant` | `break > required` (exactly 30 min fails) | `break >= required` | Yes |
| HCM-F06 | `leave.carry_forward` | Ignores the configured cap, always uses 15 days | Uses the `cap` argument | Yes, except for the 15-day cap requirement where the fault is invisible (realistic masking) |
| HCM-F07 | `eligibility.benefits_eligible` | Contractors are not excluded | Contractors and seasonal workers excluded | Yes |
| HCM-F08 | `approvals.can_approve` | Exclusive limit (`amount < limit`) | Inclusive (`amount <= limit`) | Yes |

## Known gaps that are not deliberate faults

- **Group-specific shift differentials.** `shift_differential_pay` supports only the standard rates (night 10%,
  evening 5%). Requirements for security officers (12%/6%) and clinic staff (15%/7%) therefore fail on both builds.
  Their defects remain open after the 1.1 retest, which is the correct outcome.
- **Seeded automation defects.** Two approved seeded tests (`Retail associates: fractional overtime…` and
  `Part-time employees: excess balance forfeited`) reference a mistyped module name and raise `NameError` on both
  builds. They are classified as `test_automation_defect` and no product defect is raised for them.

## Verified outcome on a fresh database

Running every approved seeded script once per build: **58 non-passing results on 1.0, 6 on 1.1** (2 automation
defects + 4 differential-rate gap). The platform end-to-end test additionally creates a new requirement, generates
tests, executes them on 1.0 (genuine HCM-F01 failure), approves the defect, retests on 1.1 and verifies the fix.
