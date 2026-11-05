"""AI quality evaluation harness over golden HCM scenarios. Scores are computed, never invented."""
from __future__ import annotations

import json
from pathlib import Path

from app.db.base import session_scope, utcnow
from app.db.models import EvalResult, EvalRun
from app.graph.execution_graph import classify_deterministic
from app.guardrails.ambiguity import detect_ambiguity
from app.guardrails.ast_validator import validate_script
from app.guardrails.clauses import split_clauses
from app.guardrails.duplicates import find_duplicates
from app.guardrails.quotes import verify_quote
from app.guardrails.sanitize import as_untrusted_block
from app.llm import prompts, router
from app.llm.schemas import AcceptanceCriteriaBatch, FailureAnalysisOut, RequirementAnalysis, TestCaseBatch

GOLDEN_PATH = Path(__file__).resolve().parents[2] / "evals" / "golden_scenarios.json"


def load_golden() -> list[dict]:
    return json.loads(GOLDEN_PATH.read_text())


def _call(chain, task, user, schema, stats):
    stats["calls"] += 1
    try:
        r = router.generate(task, prompts.SYSTEM_BASE, user, schema, chain=chain, use_cache=False)
        stats["schema_ok"] += 1
        stats["repairs"] += r.repairs
        return r.data
    except router.StructuredOutputError:
        stats["repairs"] += router.MAX_REPAIRS
        return None


def evaluate_scenario(chain, sc: dict) -> dict:
    key = sc["key"]
    clauses = split_clauses(key, sc["requirement"])
    cl = [{"key": c.key, "text": c.text} for c in clauses]
    texts = {c.key: c.text for c in clauses}
    untrusted = as_untrusted_block("REQUIREMENT", sc["requirement"])
    stats = {"calls": 0, "schema_ok": 0, "repairs": 0}
    analysis = _call(chain, "requirement_analysis", prompts.analysis_prompt(key, sc["title"], cl, untrusted),
                     RequirementAnalysis, stats)
    acs = _call(chain, "acceptance_criteria", prompts.ac_prompt(key, cl, untrusted), AcceptanceCriteriaBatch, stats)
    tests = _call(chain, "test_cases", prompts.test_prompt(key, cl, [], untrusted, False), TestCaseBatch, stats)
    items = (acs.criteria if acs else []) + (tests.tests if tests else [])
    ungrounded = 0
    for it in items:
        if any(k not in texts for k in it.clause_keys) or not verify_quote(
                it.source_quote, [texts[k] for k in it.clause_keys if k in texts]):
            ungrounded += 1
    test_list = tests.tests if tests else []
    covered = {k for t in test_list for k in t.clause_keys if k in texts}
    expected_cov = [f"{key}.C{i}" for i in sc["expected_covered_clauses"]]
    found_terms = {f["term"].lower() for c in clauses for f in detect_ambiguity(c.text)}
    if analysis:
        for ci in analysis.clauses:
            found_terms.update(a.lower() for a in ci.ambiguities)
    exp_terms = [t.lower() for t in sc["expected_ambiguity_terms"]]
    amb_hits = sum(1 for t in exp_terms if any(t in f for f in found_terms))
    dupes = find_duplicates([(str(i), t.title + " " + t.expected_result) for i, t in enumerate(test_list)])
    blob = json.dumps([t.model_dump() for t in test_list]).lower()
    forbidden = [f for f in sc.get("forbidden_outputs", []) if f.lower() in blob]
    edge_hits = [e for e in sc.get("expected_edge_cases", []) if e.lower() in blob]
    unsafe_scripts = sum(1 for t in test_list if t.script and not validate_script(t.script).valid)
    fc = sc["failure_case"]
    fa = _call(chain, "failure_analysis", prompts.failure_prompt(fc), FailureAnalysisOut, stats)
    det_cat, _ = classify_deterministic(fc.get("result_status", "failed"), fc["message"], fc["stack_trace"])
    metrics = {
        "clause_count_expected": sc["expected_clause_count"], "clause_count_parsed": len(clauses),
        "clause_coverage": round(len(covered & set(expected_cov)) / len(expected_cov), 3) if expected_cov else 1.0,
        "ungrounded_rate": round(ungrounded / len(items), 3) if items else None,
        "duplicate_rate": round(len(dupes) / len(test_list), 3) if test_list else None,
        "schema_pass_rate": round(stats["schema_ok"] / stats["calls"], 3) if stats["calls"] else None,
        "ambiguity_recall": round(amb_hits / len(exp_terms), 3) if exp_terms else 1.0,
        "traceability": round(sum(1 for t in test_list if any(k in texts for k in t.clause_keys)) / len(test_list), 3)
        if test_list else None,
        "avg_retries": round(stats["repairs"] / stats["calls"], 3) if stats["calls"] else None,
        "failure_classification_correct": (fa.category == fc["expected_category"]) if fa else False,
        "deterministic_classification_correct": det_cat == fc["expected_category"],
        "edge_cases_found": f"{len(edge_hits)}/{len(sc.get('expected_edge_cases', []))}",
        "forbidden_outputs": forbidden, "unsafe_scripts": unsafe_scripts,
        "tests_generated": len(test_list), "criteria_generated": len(acs.criteria) if acs else 0,
    }
    passed = (not forbidden and metrics["schema_pass_rate"] == 1.0 and (metrics["ungrounded_rate"] or 0) <= 0.2
              and metrics["clause_coverage"] >= 0.6)
    return {"passed": passed, "metrics": metrics}


AGG = ["clause_coverage", "ungrounded_rate", "duplicate_rate", "schema_pass_rate", "ambiguity_recall", "traceability",
       "avg_retries"]


def run_evaluation(run_id: int, eval_run_id: int, provider: str) -> dict:
    try:
        chain = router.explicit_chain(provider)
    except router.NoProviderConfigured as exc:
        with session_scope() as db:
            er = db.get(EvalRun, eval_run_id)
            er.status, er.error, er.finished_at = "failed", str(exc), utcnow()
        return {"_status": "failed", "error": str(exc)}
    golden = load_golden()
    results = []
    for i, sc in enumerate(golden):
        try:
            r = evaluate_scenario(chain, sc)
        except (router.AllProvidersFailed, router.NoProviderConfigured) as exc:
            r = {"passed": False, "metrics": {"error": str(exc)[:500]}}
        results.append((sc["key"], r))
        with session_scope() as db:
            db.add(EvalResult(eval_run_id=eval_run_id, scenario_key=sc["key"], passed=r["passed"], metrics=r["metrics"]))
        from app.services import tasks
        tasks.step(run_id, f"scenario {sc['key']}", "passed" if r["passed"] else "failed", progress=(i + 1) / len(golden))
    agg: dict = {}
    for m in AGG:
        vals = [r["metrics"].get(m) for _, r in results if isinstance(r["metrics"].get(m), (int, float))]
        agg[m] = round(sum(vals) / len(vals), 3) if vals else None
    fc = [r["metrics"].get("failure_classification_correct") for _, r in results if "error" not in r["metrics"]]
    agg["failure_classification_accuracy"] = round(sum(1 for x in fc if x) / len(fc), 3) if fc else None
    agg["scenarios_passed"] = sum(1 for _, r in results if r["passed"])
    errored = any("error" in r["metrics"] for _, r in results)
    with session_scope() as db:
        er = db.get(EvalRun, eval_run_id)
        er.metrics, er.scenario_count, er.finished_at = agg, len(results), utcnow()
        er.status = "degraded" if errored else "completed"
    return {"eval_run_id": eval_run_id, "metrics": agg}
