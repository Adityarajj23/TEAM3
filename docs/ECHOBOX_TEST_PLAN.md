# EchoBox Test Plan & Multi-Tier Verification Strategy — Project ECHO

## 1. Objectives

This test plan defines the comprehensive quality engineering strategy applied to [sohan10012/EchoBox](https://github.com/sohan10012/EchoBox.git). The plan covers multi-tiered execution from static code inspection to local in-memory harnesses, live AWS cloud integration probes, and browser E2E interaction.

---

## 2. Multi-Tier Execution Strategy

```
+-------------------------------------------------------------------------------+
|                       Tier A: Static & Source Verification                    |
|   AST Syntax Inspection | Banned Calls Check | TypeScript Compilation Build   |
+---------------------------------------+---------------------------------------+
                                        |
+---------------------------------------v---------------------------------------+
|                    Tier B: Local Test-Safe Application Runner                 |
|   21 Automated Pytest Scripts | In-Memory DynamoDB | POSIX Sandbox Isolation  |
+---------------------------------------+---------------------------------------+
                                        |
+---------------------------------------v---------------------------------------+
|                    Tier C: Live Cloud Integration Probe                       |
|   Live HTTP POST Probe to AWS Gateway | Response Code & Latency Tracking      |
+---------------------------------------+---------------------------------------+
                                        |
+---------------------------------------v---------------------------------------+
|                      Browser E2E Playwright Automation                        |
|   Local Preview Server (Port 5174) | Join Room Flows | Screenshots & Logs     |
+-------------------------------------------------------------------------------+
```

---

## 3. Test Cases Matrix (21 Tests)

| Test ID | Test Category | Target Requirement | Objective / Assertion | Automation Runner |
| :--- | :--- | :--- | :--- | :--- |
| `TC-ECHO-0001` | Positive | `ECHO-REQ-001` | Verify room creation returns HTTP 201 with 8-char ID and 24h expires_at. | Pytest Sandbox |
| `TC-ECHO-0002` | Positive | `ECHO-REQ-002` | Verify discover_rooms returns public rooms with correct message counts. | Pytest Sandbox |
| `TC-ECHO-0003` | Boundary | `ECHO-REQ-003` | Verify message boundary: 2000 chars accepted, 2001 chars rejected (400). | Pytest Sandbox |
| `TC-ECHO-0004` | Authorization | `ECHO-REQ-004` | Verify non-owner closure attempt returns 403; owner closure blocks messages. | Pytest Sandbox |
| `TC-ECHO-0005` | Data Isolation | `ECHO-REQ-005` | Verify User B cannot delete post authored by User A (HTTP 403). | Pytest Sandbox |
| `TC-ECHO-0006` | Expiration | `ECHO-REQ-006` | Verify room with expires_at in past returns HTTP 410 Gone on submit. | Pytest Sandbox |
| `TC-ECHO-0007` | Security | `ECHO-REQ-007` | Verify payload > 64KB returns HTTP 413 Payload Too Large. | Pytest Sandbox |
| `TC-ECHO-0008` | Boundary | `ECHO-REQ-008` | Detect description discrepancy: 750 chars accepted contrary to 500 doc limit. | Pytest Sandbox |
| `TC-ECHO-0009` | Security | `ECHO-REQ-009` | Detect invalid visibility (`confidential`) silently falls back to public. | Pytest Sandbox |
| `TC-ECHO-0010` | Contract | `ECHO-REQ-010` | Verify empty room ID triggers client-side validation format checks. | Pytest Sandbox |
| `TC-ECHO-0011` | Contract | `ECHO-REQ-011` | Probe live AWS Gateway; verify HTTP 500 error response shape. | HTTP Probe |
| `TC-ECHO-0012` | Positive | `ECHO-REQ-012` | Verify get_feedback returns chronological message stream. | Pytest Sandbox |
| `TC-ECHO-0013` | Boundary | `ECHO-REQ-013` | Verify reopening room within 24h succeeds; reopening expired room returns 400. | Pytest Sandbox |
| `TC-ECHO-0014` | Authorization | `ECHO-REQ-014` | Verify get_owner_rooms returns only rooms created by authenticated caller. | Pytest Sandbox |
| `TC-ECHO-0015` | Contract | `ECHO-REQ-015` | Verify Access-Control-Allow-Origin wildcard present on responses. | Pytest Sandbox |
| `TC-ECHO-0016` | Positive | `ECHO-REQ-016` | Verify health_check action returns status 200 healthy. | Pytest Sandbox |
| `TC-ECHO-0017` | Boundary | `ECHO-REQ-017` | Detect silent truncation of 120-char room name to 100 characters. | Pytest Sandbox |
| `TC-ECHO-0018` | Integration | `ECHO-REQ-018` | Verify N+1 query message count calculation in public discovery. | Pytest Sandbox |
| `TC-ECHO-0019` | Contract | `ECHO-REQ-019` | Verify accessible role='alert' on Toast notification components. | Pytest Sandbox |
| `TC-ECHO-0020` | Contract | `ECHO-REQ-020` | Verify RoomView disables textarea when room is closed or expired. | Pytest Sandbox |
| `TC-ECHO-0021` | Authorization | `ECHO-REQ-021` | Verify claim_legacy_room rejects unauthenticated requests (HTTP 401). | Pytest Sandbox |

---

## 4. Entry and Exit Criteria

- **Entry Criteria**:
  - Codebase cloned cleanly into `var/repos/EchoBox`.
  - Frontend builds cleanly via `tsc -b && vite build`.
  - `echobox_harness` available in sandbox execution root.
- **Exit Criteria**:
  - 100% of runnable local automated test cases pass in isolated sandbox.
  - Live cloud integration errors accurately preserved and documented as blockers.
  - Zero unverified or ungrounded test cases in approved state.
  - All five genuine defects documented with reproduction steps and AI root-cause analysis.
