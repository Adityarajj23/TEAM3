# Product Overview — TraceTest AI

## 1. Executive Summary

TraceTest AI is an enterprise-grade AI quality engineering and requirement verification platform. Designed for mission-critical applications—spanning enterprise Human Capital Management (Dayforce HCM) and modern cloud-native architectures—TraceTest AI bridges the gap between unstructured business requirements, code implementations, automated test suites, and defect remediation.

Unlike prototype dashboards or synthetic test generators, TraceTest AI operates as a cohesive, deterministic quality engineering harness that ingests real repositories, parses code structures, identifies edge cases, executes tests inside sandboxes, logs reproducible defects, and verifies fixes with complete auditability.

---

## 2. Core Value Proposition

| Traditional QA Challenges | TraceTest AI Engineering Solution |
| :--- | :--- |
| **Requirements Drift**: Business rules change without automated visibility into impacted test cases. | **Immutable Version Snapshots**: Cryptographic SHA-256 version hashes and automated change-impact analysis mark affected tests for re-approval. |
| **Hallucinated AI Tests**: LLMs invent endpoints, parameters, and behaviors not grounded in reality. | **Deterministic Grounding & AST Validation**: Tests must verify verbatim source quotes against cited requirement clauses and pass strict AST allowlists before execution. |
| **Flaky & Insecure Execution**: Automated test scripts execute arbitrary shell commands or drop out. | **Multi-Tiered Sandboxed Runner**: Ephemeral POSIX namespaces with CPU, memory, and network isolation limits. |
| **Vague Defect Reports**: Developers struggle to reproduce failures without exact traces. | **End-to-End Traceability**: Direct linking from defect $\rightarrow$ execution failure log $\rightarrow$ test case $\rightarrow$ acceptance criterion $\rightarrow$ requirement clause $\rightarrow$ source code lines. |
| **AI Provider Lock-In**: Platform downtime when single LLM vendor suffers outages or quota exhaustion. | **Dual Live Orchestration**: Multi-key rotation across Groq (`openai/gpt-oss-120b`) and Gemini (`gemini-2.5-flash`) with slot-level circuit breaking. |

---

## 3. Product Workspaces

TraceTest AI supports two primary enterprise operational workspaces:

### A. Dayforce Quality Engineering Workspace
Specialized for HCM, Payroll, Workforce Management, Time & Attendance, and Benefits compliance.
- Projects: `DF-PAY` (Payroll Verification), `DF-WFM` (Workforce Management), `DF-LVE` (Absence & Leave), `DF-BEN` (Benefits & Eligibility).
- Golden Reference System: Reference HCM 1.0 (baseline) and Reference HCM 1.1 (candidate fix).
- Rules: FLSA overtime, statutory minimums, meal break compliance, benefit eligibility windows.

### B. Cloud Application Verification Workspace (EchoBox Case Study)
Specialized for modern serverless, cloud-native architectures.
- Project: `ECHO` (EchoBox — Anonymous Conversation Platform).
- Ingested Target: `https://github.com/sohan10012/EchoBox.git` (React 18, Vite, AWS HTTP API Gateway, Python Lambda, DynamoDB, Cognito).
- Verification Scope: Ephemeral 24-hour expiration (HTTP 410), single-table DynamoDB querying, owner token authorization (HTTP 403), request payload sizing (64KB HTTP 413), and live cloud infrastructure probing.

---

## 4. Single-Operator Workflow

TraceTest AI is designed around a focused single-operator engineering experience:
1. **No Gratuitous Auth Screens**: Bypasses consumer-facing login and avatar menus in development and local verification mode.
2. **Deterministic Navigation**: Coherent sidebar hierarchy:
   - **Overview**: Executive coverage, suite status, and defect summaries.
   - **Requirements**: Versioned requirements, clause segmentation, and ambiguity flags.
   - **Test Cases**: Grounded test inventory, automation scripts, and validation errors.
   - **Approval Workspace**: Interactive human-in-the-loop review queue for generated tests and criteria.
   - **Suites**: Test suite composition organized by functional module.
   - **Executions**: Real-time execution logs, JUnit XML output, and browser artifacts.
   - **Defects**: Defect triage, AI root-cause analysis, and retest verification triggers.
   - **Traceability**: Bidirectional requirement-to-defect coverage matrix.
   - **Analytics**: Empirical quality metrics, pass rates, and coverage statistics.
   - **Settings**: AI provider slot status, API key rotation diagnostics, and environment configuration.

---

## 5. Architectural Quality Standards

- **Typography & Layout**: Disciplined enterprise aesthetic with Google Sans / Tahoma fallbacks, 4px/8px spacing tokens, and neutral surfaces with subtle blue chromatic accents.
- **Responsive Stability**: Resilient across six standardized breakpoints (1440px desktop, 1280px standard, 1024px tablet landscape, 768px tablet portrait, 390px mobile, 360px compact) using `min-h-[100dvh]` and `overflow-x: clip`.
- **Zero Hallucinated Metrics**: Every KPI, coverage percentage, and test result is calculated from verified database state.

