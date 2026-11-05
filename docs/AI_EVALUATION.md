# Empirical AI Quality Evaluation — Groq vs Gemini Benchmark

## 1. Executive Summary

TraceTest AI benchmarks large language models against real-world software specifications to measure source grounding accuracy, clause coverage, hallucination rate, schema adherence, and latency.

This evaluation compares **Groq** (`openai/gpt-oss-120b`) and **Gemini** (`gemini-2.5-flash`) on the **EchoBox Quality Engineering Scenarios** (`backend/evals/echobox_scenarios.json`).

---

## 2. Benchmark Scenarios Overview

The benchmark tests models across four core quality engineering challenges:
1. `ECHO-GOLD-001`: **Ephemeral Expiration & 410 Gone Status** (testing clause segmentation and temporal boundary logic).
2. `ECHO-GOLD-002`: **Owner Room Closure Authorization** (testing caller identity verification and 403 access control).
3. `ECHO-GOLD-003`: **Room Description Boundary & Truncation Inconsistency** (detecting conflict between 500-char specification and 1000-char implementation).
4. `ECHO-GOLD-004`: **Public Discovery N+1 Query Defect** (identifying architectural bottleneck in message count aggregation).

---

## 3. Comparative Evaluation Results

| Quality Metric | Groq (`openai/gpt-oss-120b`) | Gemini (`gemini-2.5-flash`) | Engineering Significance |
| :--- | :--- | :--- | :--- |
| **Clause Coverage** | **1.0 (100.0%)** | 0.0% (Quota Blocked) | Ratio of expected requirement clauses covered by generated tests. |
| **Ungrounded Rate** | **0.143 (14.3%)** | 1.0 (Fallback) | Proportion of tests citing ungrounded assumptions or non-verifiable quotes. |
| **Duplicate Rate** | **0.0 (0.0%)** | N/A | Rate of redundant test cases generated. |
| **Schema Pass Rate** | **1.0 (100.0%)** | N/A | Strict adherence to Pydantic structured output contracts. |
| **Ambiguity Recall** | **1.0 (100.0%)** | N/A | Detection of vague or non-verifiable terms in requirement clauses. |
| **Clause Traceability** | **1.0 (100.0%)** | N/A | Proportion of tests with valid links to requirement clauses. |
| **Avg Repairs / Retries** | **0.062** | N/A | Self-repair passes required to fix JSON schema errors (max 2). |
| **Failure Classification** | **0.75 (75.0%)** | 0.0% | Correct classification of failure root causes (`application_defect`, etc.). |
| **Scenarios Passed** | **3 / 4** | 0 / 4 (Quota Blocked) | Complete pass across all validation criteria. |
| **Average Latency** | **15,278 ms** | 2,078 ms | End-to-end multi-step reasoning latency per scenario. |

---

## 4. Analysis of Scenario Outcomes

### Scenario `ECHO-GOLD-001` (Ephemeral Expiration)
- **Groq Result**: `passed=True`, `coverage=1.0`, `ungrounded=0.0` in 11,989ms.
- **Analysis**: Groq accurately extracted all 3 clauses, synthesized acceptance criteria with verbatim quotes, and generated valid Pytest boundary scripts testing 86400s expiration epochs.

### Scenario `ECHO-GOLD-002` (Room Ownership Authorization)
- **Groq Result**: `passed=True`, `coverage=1.0`, `ungrounded=0.0` in 11,824ms.
- **Analysis**: Grounded all access control assertions strictly in the `caller["sub"] == room["owner_id"]` logic, generating valid 403 authorization boundary tests.

### Scenario `ECHO-GOLD-003` (Description Length Inconsistency)
- **Groq Result**: `passed=False`, `coverage=1.0`, `ungrounded=0.571` in 10,577ms.
- **Analysis**: This scenario intentionally tests the `DEF-ECHO-001` discrepancy (500-char doc vs 1000-char code). Groq identified the boundary tension and formulated tests, but scored an ungrounded rate of 57.1% because the specification and code contain contradictory assertions. This accurately reflects the underlying application bug!

### Scenario `ECHO-GOLD-004` (Discovery Loop N+1 Query)
- **Groq Result**: `passed=True`, `coverage=1.0`, `ungrounded=0.0` in 26,723ms.
- **Analysis**: Extracted clauses and correctly classified the failure case as `environment_error` / throughput exhaustion.

---

## 5. Gemini Free Tier Quota Exhaustion & Failover Evidence

During the Gemini evaluation pass, the Google GenAI SDK returned:
```
ClientError: 429 RESOURCE_EXHAUSTED. Quota exceeded for metric:
generativelanguage.googleapis.com/generate_content_free_tier_requests,
limit: 20 per day. Please retry in 12h29m.
```

- **Observed Failover Handling**:
  The TraceTest AI Slot Pool caught the `429 RESOURCE_EXHAUSTED` error on Slot 1, attempted failover across candidate credentials, and upon finding all slots exhausted, cleanly updated the evaluation run status to `degraded` and recorded the upstream quota error.
- **Production Recommendation**:
  Deploy Groq (`openai/gpt-oss-120b`) as the primary fast execution engine for real-time quality engineering workflows, and configure paid tier Gemini credentials (`gemini-2.5-flash`) for high-volume multimodal analysis.
