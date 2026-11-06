"""AI quality evaluation harness over golden HCM scenarios. Scores are computed, never invented."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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


def is_item_grounded(item: Any, texts: dict[str, str]) -> tuple[bool, str]:
    """Validates that cited clause keys exist and source_quote occurs verbatim in the clause text."""
    clause_keys = getattr(item, "clause_keys", None)
    if clause_keys is None and isinstance(item, dict):
        clause_keys = item.get("clause_keys", [])
    if not clause_keys:
        return False, "No clause_keys cited"
    unknown = [k for k in clause_keys if k not in texts]
    if unknown:
        return False, f"Unknown clause keys cited: {unknown}"
    quote = getattr(item, "source_quote", None)
    if quote is None and isinstance(item, dict):
        quote = item.get("source_quote", "")
    sources = [texts[k] for k in clause_keys if k in texts]
    if not verify_quote(quote, sources):
        return False, f"Source quote '{quote}' was not found verbatim in cited clauses {clause_keys}"
    return True, ""


def repair_ungrounded_quotes(
    chain: list[Any],
    task: str,
    initial_items: list[Any],
    schema: type[Any],
    texts: dict[str, str],
    stats: dict[str, int],
    max_attempts: int = 2,
    original_prompt: str = ""
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Inspects generated criteria or tests against deterministic quote verification.
    If ungrounded items are found, feeds back specific error and clause text in a repair loop (max 2 attempts).
    Returns (valid_items, rejected_items).
    """
    valid_items: list[dict[str, Any]] = []
    pending_items: list[dict[str, Any]] = []

    for it in initial_items:
        it_dict = it.model_dump() if hasattr(it, "model_dump") else dict(it)
        ok, reason = is_item_grounded(it_dict, texts)
        if ok:
            valid_items.append(it_dict)
        else:
            it_dict["_failure_reason"] = reason
            pending_items.append(it_dict)

    attempt = 0
    prompt_context = original_prompt or task
    while pending_items and attempt < max_attempts:
        attempt += 1
        repair_msg = prompts.quote_repair_prompt(task, prompt_context, pending_items, texts)
        repaired_batch = _call(chain, task, repair_msg, schema, stats)
        if not repaired_batch:
            break

        repaired_list = getattr(repaired_batch, "criteria", None) or getattr(repaired_batch, "tests", None) or []
        new_pending: list[dict[str, Any]] = []
        for it in repaired_list:
            it_dict = it.model_dump() if hasattr(it, "model_dump") else dict(it)
            ok, reason = is_item_grounded(it_dict, texts)
            if ok:
                valid_items.append(it_dict)
            else:
                it_dict["_failure_reason"] = reason
                new_pending.append(it_dict)
        pending_items = new_pending

    rejected_items: list[dict[str, Any]] = []
    for it in pending_items:
        desc = it.get("description") or it.get("title") or "Item"
        ck = it.get("clause_keys", [])
        q = it.get("source_quote", "")
        rejected_items.append({
            "task": task,
            "description": desc,
            "clause_keys": ck,
            "quote": q,
            "reason": f"Ungrounded: {it.get('_failure_reason', 'Quote not found verbatim')} (after {attempt} repair attempts)"
        })

    return valid_items, rejected_items


def evaluate_scenario(chain, sc: dict) -> dict:
    key = sc["key"]
    clauses = split_clauses(key, sc["requirement"])
    cl = [{"key": c.key, "text": c.text} for c in clauses]
    texts = {c.key: c.text for c in clauses}
    untrusted = as_untrusted_block("REQUIREMENT", sc["requirement"])
    stats = {"calls": 0, "schema_ok": 0, "repairs": 0}

    # 1. Requirement analysis
    analysis = _call(chain, "requirement_analysis", prompts.analysis_prompt(key, sc["title"], cl, untrusted),
                     RequirementAnalysis, stats)

    # 2. Group clauses into small focused groups (size <= 2)
    clause_groups = [cl[i:i + 2] for i in range(0, len(cl), 2)]

    all_valid_criteria: list[dict[str, Any]] = []
    all_rejected_criteria: list[dict[str, Any]] = []
    for grp in clause_groups:
        prompt_text = prompts.ac_prompt(key, grp, untrusted)
        batch = _call(chain, "acceptance_criteria", prompt_text, AcceptanceCriteriaBatch, stats)
        raw_items = batch.criteria if batch else []
        valid_acs, rej_acs = repair_ungrounded_quotes(
            chain=chain, task="acceptance_criteria", initial_items=raw_items,
            schema=AcceptanceCriteriaBatch, texts=texts, stats=stats, max_attempts=2,
            original_prompt=prompt_text
        )
        all_valid_criteria.extend(valid_acs)
        all_rejected_criteria.extend(rej_acs)

    all_valid_tests: list[dict[str, Any]] = []
    all_rejected_tests: list[dict[str, Any]] = []
    for grp in clause_groups:
        grp_keys = {c["key"] for c in grp}
        grp_crit = [ac for ac in all_valid_criteria if any(k in grp_keys for k in ac.get("clause_keys", []))]
        prompt_text = prompts.test_prompt(key, grp, grp_crit, untrusted, edge_cases=False)
        batch = _call(chain, "test_cases", prompt_text, TestCaseBatch, stats)
        raw_items = batch.tests if batch else []
        valid_t, rej_t = repair_ungrounded_quotes(
            chain=chain, task="test_cases", initial_items=raw_items,
            schema=TestCaseBatch, texts=texts, stats=stats, max_attempts=2,
            original_prompt=prompt_text
        )
        all_valid_tests.extend(valid_t)
        all_rejected_tests.extend(rej_t)

    all_rejected = all_rejected_criteria + all_rejected_tests
    total_evaluated = len(all_valid_criteria) + len(all_valid_tests) + len(all_rejected)
    ungrounded_count = len(all_rejected)

    ungrounded_quotes: list[dict[str, Any]] = [
        {
            "quote": r.get("quote"),
            "clauses": r.get("clause_keys"),
            "rationale": r.get("reason"),
            "task": r.get("task")
        }
        for r in all_rejected
    ]

    test_list = all_valid_tests
    covered = {k for t in test_list for k in t.get("clause_keys", []) if k in texts}
    expected_cov = [f"{key}.C{i}" for i in sc["expected_covered_clauses"]]
    found_terms = {f["term"].lower() for c in clauses for f in detect_ambiguity(c.text)}
    if analysis:
        for ci in analysis.clauses:
            found_terms.update(a.lower() for a in ci.ambiguities)
    exp_terms = [t.lower() for t in sc["expected_ambiguity_terms"]]
    amb_hits = sum(1 for t in exp_terms if any(t in f for f in found_terms))
    dupes = find_duplicates([(str(i), (t.get("title") or "") + " " + (t.get("expected_result") or "")) for i, t in enumerate(test_list)])
    blob = json.dumps(test_list).lower()
    forbidden = [f for f in sc.get("forbidden_outputs", []) if f.lower() in blob]
    edge_hits = [e for e in sc.get("expected_edge_cases", []) if e.lower() in blob]
    unsafe_scripts = sum(1 for t in test_list if t.get("script") and not validate_script(t["script"]).valid)
    fc = sc["failure_case"]
    fa = _call(chain, "failure_analysis", prompts.failure_prompt(fc), FailureAnalysisOut, stats)
    det_cat, _ = classify_deterministic(fc.get("result_status", "failed"), fc["message"], fc["stack_trace"])

    metrics = {
        "clause_count_expected": sc["expected_clause_count"], "clause_count_parsed": len(clauses),
        "clause_coverage": round(len(covered & set(expected_cov)) / len(expected_cov), 3) if expected_cov else 1.0,
        "ungrounded_rate": round(ungrounded_count / total_evaluated, 3) if total_evaluated else 0.0,
        "duplicate_rate": round(len(dupes) / len(test_list), 3) if test_list else 0.0,
        "schema_pass_rate": round(stats["schema_ok"] / stats["calls"], 3) if stats["calls"] else 1.0,
        "ambiguity_recall": round(amb_hits / len(exp_terms), 3) if exp_terms else 1.0,
        "traceability": round(sum(1 for t in test_list if any(k in texts for k in t.get("clause_keys", []))) / len(test_list), 3)
        if test_list else 1.0,
        "avg_retries": round(stats["repairs"] / stats["calls"], 3) if stats["calls"] else 0.0,
        "failure_classification_correct": (fa.category == fc["expected_category"]) if fa else False,
        "deterministic_classification_correct": det_cat == fc["expected_category"],
        "edge_cases_found": f"{len(edge_hits)}/{len(sc.get('expected_edge_cases', []))}",
        "forbidden_outputs": forbidden, "unsafe_scripts": unsafe_scripts,
        "ungrounded_quotes": ungrounded_quotes,
        "tests_generated": len(test_list), "criteria_generated": len(all_valid_criteria),
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
