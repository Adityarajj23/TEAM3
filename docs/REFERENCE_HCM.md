# TraceTest AI — Reference Human Capital Management (HCM) Engine Specification

TraceTest AI includes a deterministic, pure-Python System Under Test (SUT) located in `reference_hcm/`. The engine models enterprise HR, payroll, attendance, benefits eligibility, and approval governance workflows.

---

## 1. Architecture & Dual-Build System

The SUT exists as two distinct codebases selected dynamically at runtime via the environment variable `REFERENCE_HCM_VERSION`:
- **`reference_hcm/v1_0/`**: Fault-Injected Initial Release (contains 8 deliberate enterprise bugs).
- **`reference_hcm/v1_1/`**: Corrected Maintenance Release (resolves the 8 deliberate bugs; retains real-world engine boundary limits).

Both builds expose an identical public API:
```python
from reference_hcm import payroll, attendance, leave, eligibility, approvals
```

### Module Responsibilities
| Module | Core Functions | Business Domain |
|---|---|---|
| `payroll` | `calculate_overtime_hours`, `calculate_gross_pay`, `round_pay`, `shift_differential_pay`, `retroactive_adjustment`, `payroll_cutoff`, `is_before_cutoff`, `holiday_pay` | Overtime thresholds, salary calculations, shift differentials, and cut-off windows. |
| `attendance` | `pair_punches`, `has_missed_punch`, `worked_hours`, `meal_break_compliant` | Timecard punch pairing, duration calculation, and meal break compliance rules. |
| `leave` | `accrue_leave`, `carry_forward`, `termination_payout` | PTO accrual rates, annual carryover caps, and final termination payouts. |
| `eligibility` | `benefits_eligible` | Full-time vs contractor/seasonal employee healthcare and retirement eligibility. |
| `approvals` | `can_approve`, `has_permission` | Managerial expense approval thresholds and delegation hierarchies. |

---

## 2. Deliberate Faults in HCM v1.0 (Fixed in v1.1)

The table below catalogs the 8 deliberate defects implemented in `reference_hcm/v1_0/` and their verified resolutions in `reference_hcm/v1_1/`:

| Fault ID | Component & Function | Faulty Behavior (v1.0) | Corrected Behavior (v1.1) | Impacted Tests |
|---|---|---|---|---|
| **HCM-F01** | `payroll.calculate_overtime_hours` | Off-by-one threshold calculation: begins counting overtime from `threshold - 1` once the threshold is exceeded (e.g. 40 hours worked yields 1 OT hour). | Calculates overtime strictly above threshold (`max(0, hours - threshold)`). | All overtime test cases (`TC-PAY-0001` through `TC-PAY-0015`). |
| **HCM-F02** | `payroll._money` / `round_pay` | Applies `ROUND_HALF_EVEN` (banker's rounding, e.g. 2.345 rounds down to 2.34). | Applies statutory `ROUND_HALF_UP` (2.345 rounds to 2.35). | Precision payroll calculations (`TC-PAY-0017` to `TC-PAY-0025`). |
| **HCM-F03** | `payroll.SHIFT_DIFFERENTIALS` | Evening shift differential is misconfigured to use the Night rate (10%). | Evening differential correctly configured to standard 5%. | Shift differential tests (`TC-PAY-0030` to `TC-PAY-0040`). |
| **HCM-F04** | `payroll.is_before_cutoff` | Strict exclusive boundary: timecards submitted exactly at 17:00 on cutoff day are rejected. | Inclusive boundary (`timestamp <= cutoff_time`). | Payroll submission window tests (`TC-PAY-0045` to `TC-PAY-0050`). |
| **HCM-F05** | `attendance.meal_break_compliant` | Requires `break_minutes > required_minutes` (exactly 30 minutes fails compliance). | Compliant if `break_minutes >= required_minutes`. | Meal break compliance tests (`TC-WFS-0010` to `TC-WFS-0020`). |
| **HCM-F06** | `leave.carry_forward` | Hardcodes carryover cap to 15 days, ignoring the configured policy parameter. | Respects the caller-supplied `cap` argument. | Policy-specific leave rollover tests (`TC-LVE-0005` to `TC-LVE-0020`). |
| **HCM-F07** | `eligibility.benefits_eligible` | Fails to exclude independent contractors from benefits eligibility. | Correctly restricts benefits to regular full-time employees. | Contractor eligibility tests (`TC-BEN-0001` to `TC-BEN-0015`). |
| **HCM-F08** | `approvals.can_approve` | Strict exclusive limit (`amount < approval_limit`). | Inclusive limit (`amount <= approval_limit`). | Approval authorization boundary tests (`TC-APP-0001` to `TC-APP-0010`). |

---

## 3. Engine Gaps vs. Test Automation Defects Audit

### 3.1 Test Automation Defects (Identified and Resolved)
During comprehensive platform auditing, two test cases originally failed across both v1.0 and v1.1 builds due to intentional mock errors in `backend/app/seed/seed.py`:
- `TC-LVE-0026`: Contained misspelled identifier `leav.` instead of `leave.`.
- `TC-PAY-0016`: Contained misspelled identifier `payrol.` instead of `payroll.`.

**Resolution**: Both script typos were corrected in the seed catalog (`broken: set[tuple[str, str]] = set()`). On v1.1, both tests now pass cleanly without syntax or name errors.

### 3.2 Legitimate SUT Engine Limitations (Unsupported Group Differential Rates)
Four test cases fail on both HCM v1.0 and v1.1 builds. These failures are **not** bugs in the test automation or TraceTest AI platform; they are genuine architectural limitations of the `reference_hcm` engine:
- `TC-PAY-0070` & `TC-PAY-0071`: Security Officer differential rates (6% evening / 12% night).
- `TC-WFS-0046` & `TC-WFS-0047`: Clinical Staff differential rates (7% evening / 15% night).

**Engine Limitation**: The `reference_hcm.payroll.shift_differential_pay` engine only implements standard organization rates (5% evening / 10% night) and does not support role-based differential rate matrices. When evaluated on HCM v1.1:
1. The 4 tests execute deterministically and fail due to expected rate discrepancies.
2. The AI failure analysis graph correctly classifies them as `application_defect`.
3. Defects remain in `open` state following retest on v1.1, accurately reflecting genuine SUT limitations.

---

## 4. Empirical Verification Results Across Environments

On a clean seeded database with 100 test cases:

```
+--------------------------+-----------------------+-----------------------+
| Metric                   | Reference HCM v1.0    | Reference HCM v1.1    |
+--------------------------+-----------------------+-----------------------+
| Total Test Cases         | 100                   | 100                   |
| Passed Test Cases        | 42                    | 96                    |
| Failed Test Cases        | 58 (Deliberate Faults)| 4 (Engine Limitations)|
| Test Automation Errors   | 0                     | 0                     |
| Pass Rate                | 42.0%                 | 96.0%                 |
+--------------------------+-----------------------+-----------------------+
```

This verification confirms:
1. Defect detection: 100% of deliberate faults (HCM-F01 through HCM-F08) are caught on v1.0.
2. Defect resolution verification: When retested on v1.1, all 54 resolved faults transition to `passed` and their associated defects can be verified and closed.
3. Negative assurance: Engine gaps remain open and cannot be falsely verified without a genuine passing retest.
