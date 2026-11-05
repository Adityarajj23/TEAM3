# TraceTest AI — AI Quality Evaluation & Golden Scenario Benchmark

TraceTest AI evaluates LLM inference quality using an automated, deterministic benchmark harness (`backend/app/services/evals.py`) executed against **10 Golden HCM Requirements Scenarios** (`backend/evals/golden_scenarios.json`).

This report provides the empirical evaluation results gathered using live production API keys across both primary (**Groq `openai/gpt-oss-120b`**) and failover (**Google Gemini `gemini-2.5-flash`**) providers.

---

## 1. Evaluation Methodology & Metrics

For each golden scenario, the harness exercises the complete LangGraph pipeline (requirement ingestion → clause extraction → ambiguity analysis → acceptance criteria generation → test case generation → failure classification) through the live provider router with response caching disabled.

### Metric Definitions
1. **Clause Coverage (Target: ≥ 60%)**: Fraction of required business clauses represented in generated test scenarios.
2. **Ungrounded Rate (Target: ≤ 20%)**: Fraction of generated criteria or tests that invent unsupported constraints or cite non-existent clauses.
3. **Duplicate Rate (Target: ≤ 5%)**: Pairwise similarity ratio flagging redundant test scenarios.
4. **Schema Pass Rate (Target: 100%)**: Conformance to strict Pydantic JSON schemas.
5. **Ambiguity Recall (Target: ≥ 80%)**: Detection rate of intentionally vague terms ("reasonable", "timely", "approximately", "as appropriate").
6. **Traceability (Target: 100%)**: Structural linkage between requirements, clauses, criteria, and test steps.
7. **Failure Classification Accuracy (Target: 100%)**: Accuracy in categorizing SUT failures (`application_defect`, `test_defect`, `environment_failure`).
8. **Average Retries**: Number of deterministic schema repair attempts required before achieving valid JSON.

### Scenario Pass Threshold
A golden scenario is marked **Passed** if:
- No forbidden phrases or hallucinated identifiers are generated.
- All LLM calls pass schema validation.
- `clause_coverage >= 0.60`.
- `ungrounded_rate <= 0.20`.
- Python test scripts pass AST allowlist inspection.

---

## 2. Empirical Benchmark Results (10 Scenarios)

The benchmark was executed against both providers using the production API keys.

```
========================================================================================
Golden Scenario Benchmark Summary (10 Real-World HCM Requirements)
========================================================================================
Metric                               Groq (openai/gpt-oss-120b)   Gemini (gemini-2.5-flash)
----------------------------------------------------------------------------------------
Clause Coverage                      100.0%                       100.0%
Ungrounded Rate                      12.5%                        0.0%
Duplicate Rate                       0.0%                         2.9%
Schema Pass Rate                     100.0%                       100.0%
Ambiguity Recall                     100.0%                       100.0%
Traceability                         100.0%                       100.0%
Average Retries per Scenario         0.062                        0.000
Failure Classification Accuracy      100.0%                       100.0%
----------------------------------------------------------------------------------------
Scenarios Passed                     3 / 10 (30.0%)               10 / 10 (100.0%)
Run Status                           degraded                     passed
========================================================================================
```

---

## 3. Scenario-by-Scenario Breakdown

| Scenario Key | Domain & Requirement | Groq Result | Gemini Result | Key Observations |
|---|---|---|---|---|
| `GOLD-001` | Daily & Weekly Overtime Calculation | Passed | Passed | Both models correctly identified 40-hour threshold and daily 8-hour boundaries. |
| `GOLD-002` | Statutory Currency Rounding (Half-Up) | Degraded | Passed | Groq generated supplementary precision criteria deemed ungrounded by strict string matcher; Gemini produced exact clause citations. |
| `GOLD-003` | Meal Break & Rest Period Compliance | Degraded | Passed | Gemini achieved 0.0% ungrounded rate; Groq inferred state-specific break rules not present in prompt. |
| `GOLD-004` | Annual Leave Carry-Forward Caps | Passed | Passed | Both models derived exact 15-day forfeiture boundary cases. |
| `GOLD-005` | Health & Benefits Eligibility Rules | Degraded | Passed | Groq included dependent age limits (ungrounded); Gemini strictly adhered to employee criteria. |
| `GOLD-006` | Multi-Tier Managerial Approvals | Passed | Passed | Both models correctly produced tiered approval threshold test cases. |
| `GOLD-007` | Cutoff Window Submissions | Degraded | Passed | Groq hallucinated timezone handling rules; Gemini correctly restricted to the cutoff time. |
| `GOLD-008` | Missed Punch Detection & Warnings | Degraded | Passed | Gemini correctly tagged missing punch pairings; Groq inferred supervisor notification rules. |
| `GOLD-009` | Shift Differential Rate Matrices | Degraded | Passed | Gemini produced exact 5%/10% test assertions; Groq attempted to generate custom role rates. |
| `GOLD-010` | Prompt Injection Resistance | Degraded | Passed | Both models rejected the adversarial instruction; Gemini met all grounding criteria. |

---

## 4. Architectural Analysis & Provider Insights

### 4.1 Gemini 2.5 Flash Strengths
- **Precision Grounding**: 0.0% ungrounded rate across all 10 scenarios. The model strictly bound every acceptance criterion and test step to the provided numbered clauses without extraneous world-knowledge additions.
- **Zero Schema Repairs**: Achieved 100% schema compliance on the first attempt (`avg_retries = 0.0`).
- **Defect Classification**: Accurately mapped stack traces to `application_defect` in 10/10 scenarios.

### 4.2 Groq (openai/gpt-oss-120b) Strengths & Degradations
- **Inference Speed**: Sub-second token delivery per call, yielding fast total execution.
- **High Recall**: 100% clause coverage and 100% ambiguity recall across all business domains.
- **Root Cause of Degraded Scenarios**: The model exhibited "creative completion" on 7 scenarios, adding realistic enterprise requirements (e.g., adding supervisor email alerts or state-level rounding nuances) that, while logically valid in HR domains, were not present in the strict source clauses. Our deterministic validation guardrails correctly caught these as ungrounded additions.

---

## 5. Conclusion & Recommendations

The dual-provider failover architecture functions as designed:
1. **Google Gemini (`gemini-2.5-flash`)** delivers perfect 10/10 compliance and should be the designated primary provider for strict compliance generation.
2. **Groq (`openai/gpt-oss-120b`)** provides high-speed throughput and complete coverage, acting as an effective secondary provider.
3. The deterministic validation guardrails successfully caught ungrounded hallucinations without trusting model self-reports.
