"""AI Evaluation Runner: Evaluates Groq vs Gemini on EchoBox Scenarios."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.db.base import session_scope, utcnow
from app.db.models import EvalResult, EvalRun
from app.llm import router
from app.services.evals import AGG, evaluate_scenario

ECHBOX_SCENARIOS_PATH = Path(__file__).resolve().parents[2] / "evals" / "echobox_scenarios.json"


def evaluate_provider_on_echobox(provider_name: str, model_name: str) -> dict[str, Any]:
    print(f"--- Running AI Evaluation for {provider_name} ({model_name}) ---")
    scenarios = json.loads(ECHBOX_SCENARIOS_PATH.read_text())
    chain = router.explicit_chain(provider_name)

    eval_run_id = None
    with session_scope() as db:
        eval_run = EvalRun(
            provider=provider_name,
            model=model_name,
            status="running",
            scenario_count=len(scenarios),
            started_at=utcnow()
        )
        db.add(eval_run)
        db.commit()
        eval_run_id = eval_run.id

    results = []
    for sc in scenarios:
        t0 = time.time()
        try:
            r = evaluate_scenario(chain, sc)
        except (router.AllProvidersFailed, router.NoProviderConfigured, Exception) as exc:
            r = {"passed": False, "metrics": {"error": str(exc)[:500], "clause_coverage": 0.0, "ungrounded_rate": 1.0}}
        dur_ms = int((time.time() - t0) * 1000)
        r["metrics"]["latency_ms"] = dur_ms
        results.append((sc["key"], r))

        with session_scope() as db:
            db.add(EvalResult(
                eval_run_id=eval_run_id,
                scenario_key=sc["key"],
                passed=r["passed"],
                metrics=r["metrics"],
                notes=f"Evaluated on {provider_name} ({model_name}) in {dur_ms}ms"
            ))
        print(f"  [{sc['key']}] passed={r['passed']} coverage={r['metrics'].get('clause_coverage')} ungrounded={r['metrics'].get('ungrounded_rate')} in {dur_ms}ms")

    agg: dict[str, Any] = {}
    for m in AGG:
        vals = [r["metrics"].get(m) for _, r in results if isinstance(r["metrics"].get(m), (int, float))]
        agg[m] = round(sum(vals) / len(vals), 3) if vals else None

    fc = [r["metrics"].get("failure_classification_correct") for _, r in results if "error" not in r["metrics"]]
    agg["failure_classification_accuracy"] = round(sum(1 for x in fc if x) / len(fc), 3) if fc else 0.0
    agg["scenarios_passed"] = sum(1 for _, r in results if r["passed"])
    agg["avg_latency_ms"] = round(sum(r["metrics"].get("latency_ms", 0) for _, r in results) / len(results), 1)

    errored = any("error" in r["metrics"] for _, r in results)
    with session_scope() as db:
        er = db.get(EvalRun, eval_run_id)
        if er:
            er.metrics = agg
            er.status = "degraded" if errored else "completed"
            er.finished_at = utcnow()

    print(f"Evaluation finished for {provider_name}: {agg}\n")
    return {"eval_run_id": eval_run_id, "provider": provider_name, "metrics": agg}


def run_comparative_ai_evaluation():
    settings = get_settings()
    groq_res = evaluate_provider_on_echobox("groq", settings.groq_model)
    gemini_res = evaluate_provider_on_echobox("gemini", settings.gemini_model)
    return {
        "groq": groq_res,
        "gemini": gemini_res
    }


if __name__ == "__main__":
    report = run_comparative_ai_evaluation()
    print("Comparative AI Evaluation Complete:\n", json.dumps(report, indent=2))
