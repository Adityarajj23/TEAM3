# Defect Management & Discrepancy Ledger — TraceTest AI

## 1. Overview

The Defect Management subsystem tracks defects discovered through automated test failures, static analysis discrepancies, and live cloud probe results. TraceTest AI integrates deterministic triage states, automated AI failure root-cause analysis, and regression retest verification.

---

## 2. Defect Lifecycle State Machine

```
   [ open ] ----------> [ triaged ] ----------> [ assigned ]
      |                      |                       |
      v                      v                       v
[ dismissed ]          [ in_progress ]         [ in_progress ]
                             |
                             v
                         [ fixed ]
                             |
                             v
                    [ ready_for_retest ]
                             |
                   +---------+---------+
                   |                   |
                   v                   v
             [ verified ]        [ reopened ]
                   |
                   v
               [ closed ]
```

- `open`: Newly logged defect awaiting review.
- `triaged`: Categorized by severity and priority.
- `assigned`: Assigned to an engineering owner.
- `in_progress`: Active fix development underway.
- `fixed`: Patch developed in code.
- `ready_for_retest`: Target environment updated for automated verification.
- `verified`: Automated retest passed in execution sandbox.
- `closed`: Verified fix archived.
- `reopened`: Retest failed; defect reopened.

---

## 3. Discovered EchoBox Defects (`DEF-ECHO-001` through `DEF-ECHO-005`)

### DEF-ECHO-001: Description Length Inconsistency (Doc: 500 chars vs Code: 1000 chars)
- **Severity**: `medium` | **Priority**: `p3` | **Status**: `open`
- **Linked Requirement**: `ECHO-REQ-008` | **Linked Test**: `TC-ECHO-0008`
- **Location**: `backend/lambda_function.py:167` vs `README.md`
- **Defect Description**: The README and security audit state `room_description` has a maximum limit of 500 characters. `lambda_function.py` slices to 1000 characters (`clean_desc = room_desc[:1000]`), allowing 501–1000 character strings to be stored.
- **Root Cause**: Constant mismatch during initial Lambda implementation.
- **Recommended Fix**:
  ```python
  if len(room_desc) > 500:
      return response(400, {"error": "Room description cannot exceed 500 characters"})
  clean_desc = room_desc[:500]
  ```

### DEF-ECHO-002: Silent Truncation on Room Name and Description
- **Severity**: `medium` | **Priority**: `p3` | **Status**: `triaged`
- **Linked Requirement**: `ECHO-REQ-017` | **Linked Test**: `TC-ECHO-0017`
- **Location**: `backend/lambda_function.py:166-167`
- **Defect Description**: Inputs exceeding 100 characters for `room_name` or 1000 characters for `room_desc` are silently truncated with Python slices (`[:100]`, `[:1000]`) rather than returning client error `HTTP 400 Bad Request`.
- **Root Cause**: Defensive slicing without explicit length validation check.
- **Recommended Fix**:
  ```python
  if len(room_name) > 100:
      return response(400, {"error": "Room name cannot exceed 100 characters"})
  ```

### DEF-ECHO-003: Invalid Visibility Value Defaults Silently to Public Space
- **Severity**: `high` | **Priority**: `p2` | **Status**: `triaged`
- **Linked Requirement**: `ECHO-REQ-009` | **Linked Test**: `TC-ECHO-0009`
- **Location**: `backend/lambda_function.py:162-164`
- **Defect Description**: If `visibility` is not in `("public", "private")`, it defaults to `"public"`. Typos like `"privat"` or `"confidential"` silently expose private rooms in the public discovery partition (`DISCOVERY#PUBLIC`).
- **Root Cause**: Fallback assignment rather than strict enumeration validation.
- **Recommended Fix**:
  ```python
  if visibility not in ("public", "private"):
      return response(400, {"error": "Visibility must be either 'public' or 'private'"})
  ```

### DEF-ECHO-004: Discovery Loop N+1 Query Performance Bottleneck
- **Severity**: `high` | **Priority**: `p2` | **Status**: `in_progress`
- **Linked Requirement**: `ECHO-REQ-018` | **Linked Test**: `TC-ECHO-0018`
- **Location**: `backend/lambda_function.py:269-273`
- **Defect Description**: In `discover_rooms`, the Lambda loops through all public rooms and executes a secondary query with `Select="COUNT"` for each room to count messages. For $N$ rooms, this causes $N+1$ DynamoDB roundtrips.
- **Root Cause**: Unmaintained counter attribute on `ROOM#{id}` metadata record.
- **Recommended Fix**:
  Maintain `message_count` atomically on the room metadata item during `submit_feedback` using DynamoDB update expression `ADD message_count :one`.

### DEF-ECHO-005: Live AWS API Gateway Returns HTTP 500 Server Error
- **Severity**: `critical` | **Priority**: `p1` | **Status**: `open`
- **Linked Requirement**: `ECHO-REQ-011` | **Linked Test**: `TC-ECHO-0011`
- **Location**: Live Cloud Endpoint `https://<api-id>.execute-api.ap-south-1.amazonaws.com`
- **Defect Description**: The production AWS API Gateway returns `HTTP 500 Internal Server Error` with `{"error": "Internal server error"}` on public actions.
- **Root Cause**: DynamoDB table `EchoBox` is unseeded in region `ap-south-1` or Lambda execution role lacks IAM permission for `dynamodb:Query`.
- **Recommended Fix**:
  Provision DynamoDB table `EchoBox` and verify IAM policy `arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess` or granular table policy on the Lambda role.

