# Test Generation & Verification Guardrails — TraceTest AI

## 1. Overview

TraceTest AI generates grounded, executable test cases from structured requirement clauses and acceptance criteria. Unlike unconstrained code generators, all generated tests must pass deterministic safety, quotation verification, duplication detection, and AST allowlist checks before being permitted into the execution queue.

---

## 2. Test Case Classification Taxonomy

TraceTest AI organizes tests across nine discrete quality categories:

| Test Type | Objective | EchoBox Example |
| :--- | :--- | :--- |
| **Positive** | Verify nominal happy-path execution against functional specification. | `TC-ECHO-0001`: Public room creation returns HTTP 201 with 8-character ID. |
| **Negative** | Verify error handling and validation on malformed inputs. | `TC-ECHO-0003`: Oversized payload (>2000 chars) returns HTTP 400. |
| **Boundary** | Test exact edge values (thresholds, length limits, epoch timestamps). | `TC-ECHO-0008`: Room description limit testing at 500, 750, and 1000 chars. |
| **Authorization** | Verify access control boundaries, owner secrets, and token validation. | `TC-ECHO-0004`: Non-owner attempting room closure returns HTTP 403. |
| **Data Isolation** | Verify multi-tenant or multi-user boundary security (no cross-user leakage). | `TC-ECHO-0005`: User B cannot delete post authored by User A. |
| **Contract** | Verify RPC action schema, HTTP status codes, and JSON response shape. | `TC-ECHO-0010`: Empty room ID input triggers client validation feedback. |
| **Integration** | Test interactions across multiple domain modules (e.g. discovery + count). | `TC-ECHO-0018`: Public discovery secondary query message count aggregation. |
| **Security** | Verify abuse prevention, request size limits, and sanitization. | `TC-ECHO-0007`: 64KB request payload size limit returns HTTP 413. |
| **Expiration** | Test ephemeral lifecycle boundaries and time-decay rules. | `TC-ECHO-0006`: Expired room returns HTTP 410 Gone on message submission. |

---

## 3. Four-Step Deterministic Validation Pipeline

Before any generated test can be approved or executed, it must pass four deterministic checks:

```
[ Generated Test Case ]
           |
           v
  1. Clause Citation Check
     - Must cite at least one valid clause key (e.g. ECHO-REQ-001.C1).
     - Unknown or hallucinated clause keys result in immediate invalidation.
           |
           v
  2. Verbatim Quote Verification
     - Source quote cited in test must verify verbatim against cited clause text.
     - Normalized text comparison strips whitespace variance.
           |
           v
  3. AST Safety Allowlist
     - Python AST validator walks the syntax tree.
     - Rejects any dangerous modules, file I/O, network sockets, eval/exec, or while loops.
           |
           v
  4. Duplicate Suppression
     - Signature comparison against sibling tests in the same requirement.
     - Jaccard similarity $\ge 0.9$ marks test as duplicate of existing test case.
           |
           v
[ Status: Valid / Invalid ] ---> Logged with exact validation errors
```

---

## 4. AST Allowlist Enforcement (`ast_validator.py`)

Test automation scripts targeting Pytest are inspected using Python's `ast` module.

### Allowed Imports
- `pytest`, `decimal`, `datetime`, `math`, `re`, `json`, `dataclasses`, `typing`, `fractions`
- Domain packages: `reference_hcm.*`, `echobox_harness.*`
- Browser packages (when runner is Playwright): `playwright`, `playwright.sync_api`

### Banned Constructs
- **Banned Functions**: `open`, `eval`, `exec`, `compile`, `__import__`, `globals`, `locals`, `vars`, `getattr`, `setattr`, `input`, `breakpoint`
- **Banned Attributes**: `__class__`, `__bases__`, `__subclasses__`, `__globals__`, `__dict__`, `__code__`
- **Banned Statements**: `global`, `nonlocal`, `while` (prevents infinite loops), `async` / `await` (unless managed by runner).

---

## 5. Human-in-the-Loop Approval Workspace

Every valid test case enters the Approval Workspace in `pending_review` status:
- **Reviewer Actions**:
  - `Approve`: Test transitions to `approved`, unlocking execution readiness.
  - `Reject`: Test transitions to `rejected` with mandatory reason note.
  - `Request Changes`: Marks test for revision.
  - `Edit Script`: Allows QA engineer to adjust test data, assertions, or steps while retaining version history in `TestCaseVersion`.

