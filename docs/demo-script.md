# TraceTest AI — 10-Minute Executive & Technical Demo Script

**Presenter Run of Show & Live Walkthrough Guide**  
*Target Audience: VP of Engineering, Lead QA Architect, Security Reviewer, Enterprise Customer*  
*Demonstration Environment: `http://127.0.0.1:5173` (Frontend) | `http://127.0.0.1:8000` (Backend API)*  
*Active Target Repository: `https://github.com/sohan10012/EchoBox.git` (`ECHO`)*  

---

## Run of Show Timeline (10 Minutes Total)

```
[0:00 - 1:00]  Stage 1: System Overview, Security Posture & Workspace Context
[1:00 - 2:30]  Stage 2: Repository Connection, AST Analysis & Architecture Mapping
[2:30 - 4:00]  Stage 3: Grounded Requirement Decomposition & Provenance Tracking
[4:00 - 5:30]  Stage 4: Automated Test Generation & Dual-Control Human Review Gate
[5:30 - 7:30]  Stage 5: Multi-Tiered Sandboxed Execution (Moto AWS vs Live Remote)
[7:30 - 9:00]  Stage 6: Evidence-Classified Defect Triage & Verification Retesting
[9:00 - 10:00] Stage 7: Full Traceability Matrix, Analytics & Q&A Conclusion
```

---

## Detailed Step-by-Step Presenter Script

### [0:00 - 1:00] Stage 1: System Overview & Command Center
- **Action**: Open the browser to `http://127.0.0.1:5173`. Select the **ECHO** workspace from the project selector.
- **Spoken Script**:
  > *"Welcome to TraceTest AI. TraceTest AI is an enterprise-grade AI software quality engineering platform that closes the gap between business specifications and executable reality. Unlike generic test generation tools that hallucinate assertions or mock test passes, TraceTest AI ingests real codebases, extracts verifiable requirements, executes tests in strictly isolated sandboxes, and classifies real defects with empirical evidence.*
  >
  > *Looking at our Command Center top bar, notice our strict security invariants: we are bound locally to `127.0.0.1` with host-header validation, our active session is signed with `SameSite=Strict` and `HttpOnly` cookies, and our sandbox isolation level indicates `netns+rlimits`—full Linux network namespace and resource limit containment.*
  >
  > *Prominently displayed across the top is our guided 6-stage QA journey: Connect, Analyze, Requirements, Test Generation, Execute, and Defects. Every stage reflects real, persisted records in our ACID-compliant SQLite WAL database."*

---

### [1:00 - 2:30] Stage 2: Repository Connection & AST Analysis
- **Action**: Click the **Connect / Analyze** stages or navigate to the repository metadata panel. Click **Connect GitHub Repository** dialog to show connection options.
- **Spoken Script**:
  > *"Let's examine how a project enters TraceTest AI. Here we have connected EchoBox, a real public serverless application featuring AWS API Gateway, Lambda, DynamoDB Single Table design, and dual Cognito user pools.*
  >
  > *Notice that we ingest target repositories via hardened git subprocesses: credentials use an isolated `GIT_ASKPASS` transient script with 0700 permissions so tokens never touch process argument vectors or `.git/config` on disk. We pin the exact commit SHA—`b3740a62ad41`—to guarantee historical immutability.*
  >
  > *During ingestion, our static AST analyzer automatically mapped the entire application architecture: 8 logical domain modules (including Room Lifecycle, Chat, Ownership, and Expiry), 13 discrete RPC actions, and performed an automated regex security scan verifying zero hardcoded credentials."*

---

### [2:30 - 4:00] Stage 3: Grounded Requirements & Provenance
- **Action**: Navigate to `/requirements`. Open requirement `ECHO-REQ-001` (Public Room Creation) and `ECHO-REQ-003` (Room Expiry & TTL).
- **Spoken Script**:
  > *"Moving to the Requirements stage, TraceTest AI has generated 21 grounded requirements covering all 8 modules. What makes our requirements engine unique is strict provenance.*
  >
  > *Every requirement tracks its origin: `documented` (extracted from README and technical specs), `inferred_from_code` (derived via AST analysis), or `manual`. Inferred requirements automatically start in `needs_confirmation` status and cannot generate approved tests until a QA engineer validates them.*
  >
  > *Inside `ECHO-REQ-001`, notice our atomic clauses—`C1`, `C2`, `C3`. Every single clause links to exact source file lines (`backend/lambda_function.py:214-250`) and contains verbatim text quotes verified by our deterministic quote-checking guardrail. If an LLM attempts to fabricate a clause or cite nonexistent code, our guardrail rejects it immediately."*

---

### [4:00 - 5:30] Stage 4: Test Generation & Dual-Control Review Gate
- **Action**: Navigate to `/tests`, then click **Review Queue** (`/tests/review`).
- **Spoken Script**:
  > *"From these grounded clauses, TraceTest AI synthesizes traceable test cases. We currently have 21 test cases—`TC-ECHO-0001` through `TC-ECHO-0021`—each asserting specific clause requirements.*
  >
  > *To ensure enterprise governance, we enforce the Four-Eyes Principle in our Review Queue. An AI agent or QA author cannot self-approve generated test scripts. A senior reviewer must inspect the test script, verify the test data, and approve it. Once approved, the test script's SHA-256 digest is cryptographically locked into the test case version. If the script is tampered with, it automatically transitions to `needs_reapproval`."*

---

### [5:30 - 7:30] Stage 5: Multi-Tiered Sandboxed Execution
- **Action**: Navigate to `/executions`. Click on execution `EX-000001`, then inspect execution `EX-ECHO-LIVE-001`.
- **Spoken Script**:
  > *"Now for execution. TraceTest AI adheres to a strict rule: never fake an execution pass, and never combine sandbox mocks with live remote endpoints.*
  >
  > *In execution `EX-000001`, we executed 21 tests in Tier B. Crucially, this is not an in-memory simulation; our harness loads the real `backend/lambda_function.py` from the target repository and executes it against an in-process mocked DynamoDB table powered by `moto`. It ran in 1.92 seconds inside our POSIX sandbox with `netns+rlimits` isolation, achieving a 100% pass rate for compliant functional paths.*
  >
  > *Now look at execution `EX-ECHO-LIVE-001`. This was a live probe against the real deployed AWS API Gateway endpoint (`https://bnbpmiljw9.execute-api.ap-south-1.amazonaws.com`). The live endpoint returned HTTP 500 Internal Server Error in 574ms because the upstream DynamoDB tables were unseeded. We recorded this honestly as an external infrastructure blocker rather than faking a success."*

---

### [7:30 - 9:00] Stage 6: Evidence-Classified Defect Management
- **Action**: Navigate to `/defects`. Inspect `DEF-ECHO-001` and `DEF-ECHO-006`.
- **Spoken Script**:
  > *"Because our execution is honest, our defects are grounded in real evidence. We have 6 tracked defects, each labeled with its exact `evidence_type`:*
  >
  > *1. `DEF-ECHO-001` (`static_analysis`): A specification discrepancy where documentation allows 500 characters for room descriptions, but the Lambda code permits 1000.*
  > *2. `DEF-ECHO-002` (`execution_failure`): Silent slicing of oversized strings instead of returning HTTP 400 Bad Request.*
  > *3. `DEF-ECHO-003` (`execution_failure`): Invalid visibility parameters defaulting to public rooms.*
  > *4. `DEF-ECHO-004` (`static_analysis`): An N+1 query amplification loop in room discovery.*
  > *5. `DEF-ECHO-005` (`execution_failure`): Upstream live AWS API Gateway HTTP 500.*
  > *6. `DEF-ECHO-006` (`static_analysis`): Critical security vulnerability. In `lambda_function.py:120-146`, the token fallback decodes JWT claims without cryptographic RSA signature verification against Cognito JWKS, permitting token forgery.*
  >
  > *Notice that every defect provides full reproduction steps, expected vs actual behavior, and an integrated 'Run Retest' button that executes the linked test inside the sandbox to verify code fixes."*

---

### [9:00 - 10:00] Stage 7: Full Traceability Matrix & Conclusion
- **Action**: Navigate to `/traceability`. Show the interactive matrix and export options.
- **Spoken Script**:
  > *"Finally, we come to the Traceability Matrix. Here, every business requirement maps to its exact clauses, acceptance criteria, test cases, execution outcomes, and open defects.*
  >
  > *Compliance and audit teams can export this entire matrix as CSV or PDF at any time. TraceTest AI gives engineering organizations total confidence that what was requested in the specification is what is built, tested, and running in production.*
  >
  > *Thank you. I'd be glad to take any questions."*

