# AI evaluation report

## Status

| Provider | Model | Run | Result |
|---|---|---|---|
| Groq | `openai/gpt-oss-120b` | **Not run** | No `GROQ_API_KEY` was available in the build environment |
| Gemini | `gemini-2.0-flash` | **Not run** | No `GEMINI_API_KEY` was available |
| Fixture (MockProvider) | `fixture-v1` | Run in the automated test suite | Validates the harness only; not a model-quality measurement |

No real model scores are claimed. Run an evaluation from **AI Evaluations** once a key is configured; results are
stored in `eval_runs` / `eval_results` and shown with provider and model.

## Harness

- 10 golden scenarios in `backend/evals/golden_scenarios.json` covering overtime, rounding, meal breaks,
  carry-forward caps, eligibility, approval limits, cut-off, missed punches, shift differentials and a
  prompt-injection case. Each defines the expected clause count, expected ambiguity terms, clauses that must be
  covered, expected edge-case values, forbidden outputs and a failure sample with its expected category.
- For each scenario the harness calls requirement analysis, acceptance-criteria and test generation, and failure
  analysis through the real provider router (no cache), then computes:
  clause coverage, ungrounded output rate (unknown clause or unverified quote), duplicate test rate, schema-pass
  rate, ambiguity recall (lexicon plus model), requirement-to-test traceability, average repair attempts and
  failure-classification accuracy. It also records forbidden outputs and scripts that fail the AST allowlist.
- A scenario passes when it has no forbidden output, every call passed schema validation, ungrounded rate ≤ 20% and
  clause coverage ≥ 60%.
