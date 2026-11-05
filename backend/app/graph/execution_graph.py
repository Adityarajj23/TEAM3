"""LangGraph failure-analysis and defect workflow.

(approved_test -> execution_precheck -> sandbox_execution -> result_parser are performed by the execution
service and produce the persisted ExecutionResult this graph starts from.)

execution_precheck -> failure_classifier -> evidence_analysis -> defect_recommendation
    -> (interrupt) human_approval -> defect_creation

Retest and reporting are user-initiated operations on the resulting defect.
"""
from __future__ import annotations

import re
import sqlite3
import threading
from typing import Any, TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from sqlalchemy import select

from app.core.config import get_settings
from app.db.base import session_scope, utcnow
from app.db.models import Defect, Environment, Execution, ExecutionResult, Requirement, TestCase
from app.graph.requirement_graph import _llm  # shared guarded LLM call
from app.llm import prompts
from app.llm.schemas import FailureAnalysisOut
from app.services import audit, tasks
from app.services.keys import next_key

_FN = re.compile(r"(?:payroll|attendance|leave|eligibility|approvals)\.(\w+)")


def classify_deterministic(status: str, message: str, trace: str) -> tuple[str, list[str]]:
    text = f"{message}\n{trace}"
    facts = []
    if status == "timed_out" or "timed out" in text.lower():
        return "timeout", ["Execution exceeded the sandbox time limit"]
    if "Rejected by AST allowlist" in text:
        return "test_automation_defect", ["Script was rejected by the AST allowlist before execution"]
    for err in ("SyntaxError", "NameError", "ImportError", "ModuleNotFoundError", "AttributeError", "TypeError",
                "fixture '"):
        if err in text:
            return "test_automation_defect", [f"{err} raised while running the test code"]
    if "Network access is disabled" in text:
        return "environment_failure", ["Test attempted network access inside the sandbox"]
    if "PermissionError" in text or "Permission denied" in text:
        return "permission_issue", ["A permission error was raised"]
    if "ValueError" in text and "reference_hcm" in text:
        return "data_validation_failure", ["Reference HCM rejected the input with ValueError"]
    if "MemoryError" in text or "No result reported" in text:
        return "environment_failure", ["Interpreter failed to report a result"]
    if "assert" in text.lower():
        m = re.search(r"assert (.+)", message)
        facts.append(f"Assertion failed: {m.group(1)[:200] if m else message[:200]}")
        return "application_defect", facts
    return "unknown", [message[:200] or "No failure message"]


class ExecState(TypedDict, total=False):
    result_id: int
    run_id: int
    actor_id: int | None
    precheck_ok: bool
    evidence: dict
    category: str
    observed_facts: list[str]
    ai: dict
    defect_id: int
    decision: str
    duplicate_warning: list[str]


def execution_precheck(state: ExecState) -> ExecState:
    with session_scope() as db:
        r = db.get(ExecutionResult, state["result_id"])
        t = db.get(TestCase, r.test_case_id)
        ex = db.get(Execution, r.execution_id)
        env = db.get(Environment, ex.environment_id)
        req = db.get(Requirement, t.requirement_id)
        ok = r.status in ("failed", "error", "timed_out")
        evidence: dict[str, Any] = {"result_status": r.status, "message": r.message[:3000], "stack_trace": r.stack_trace[-6000:],
                    "stdout": r.stdout[-2000:], "test_key": t.key, "test_title": t.title,
                    "expected_result": t.expected_result, "script": (t.script or "")[:4000],
                    "script_hash": r.script_hash, "environment": env.name, "hcm_version": ex.hcm_version,
                    "execution": ex.key, "requirement": req.key, "clause_keys": t.clause_keys}
        related = db.execute(select(TestCase.key).join(ExecutionResult, ExecutionResult.test_case_id == TestCase.id)
                             .where(ExecutionResult.execution_id == ex.id, ExecutionResult.id != r.id,
                                    ExecutionResult.status.in_(["failed", "error"]))).scalars().all()
        fns = set(_FN.findall(evidence["script"]))
        rel = []
        for key in related:
            other = db.execute(select(TestCase.script).where(TestCase.key == key)).scalar() or ""
            if fns & set(_FN.findall(other)):
                rel.append(key)
        evidence["related_failures"] = rel[:20]
    tasks.step(state["run_id"], "execution_precheck", "completed" if ok else "skipped", {"status": r.status}, 0.15)
    return {"precheck_ok": ok, "evidence": evidence}


def failure_classifier(state: ExecState) -> ExecState:
    ev = state["evidence"]
    cat, facts = classify_deterministic(ev["result_status"], ev["message"], ev["stack_trace"])
    tasks.step(state["run_id"], "failure_classifier", detail={"category": cat}, progress=0.35)
    return {"category": cat, "observed_facts": facts}


def evidence_analysis(state: ExecState) -> ExecState:
    st = {"run_id": state["run_id"], "invalid_items": [], "provider_errors": [], "providers_used": []}
    res, extra = _llm(st, "failure_analysis", prompts.failure_prompt(state["evidence"]), FailureAnalysisOut)
    if res:
        ai = {**res.data.model_dump(), "provider": res.provider, "model": res.model, "status": "ok"}
    else:
        ai = {"status": "unavailable", "errors": extra.get("provider_errors", []) +
              [i["error"] for i in extra.get("invalid_items", [])]}
    tasks.step(state["run_id"], "evidence_analysis", "completed" if res else "degraded", {}, 0.6)
    return {"ai": ai}


def defect_recommendation(state: ExecState) -> ExecState:
    ev, ai = state["evidence"], state.get("ai", {})
    analysis = {
        "deterministic_category": state["category"], "observed_facts": state["observed_facts"],
        "ai": ai, "related_failures": ev.get("related_failures", []),
        "confirmed": False,
        "note": "Categories are hypotheses until a human approves the defect.",
        "analysed_at": utcnow().isoformat(),
    }
    with session_scope() as db:
        r = db.get(ExecutionResult, state["result_id"])
        r.failure_analysis = analysis
        t = db.get(TestCase, r.test_case_id)
        ex = db.get(Execution, r.execution_id)
        if state["category"] not in ("application_defect", "data_validation_failure", "unknown") and \
                ai.get("category") != "application_defect":
            skip = True
        else:
            skip = False
    if skip:
        tasks.step(state["run_id"], "defect_recommendation", "skipped",
                   {"reason": f"category {state['category']} is not a product defect"}, 0.8)
        return {}
    with session_scope() as db:
        r = db.get(ExecutionResult, state["result_id"])
        t = db.get(TestCase, r.test_case_id)
        ex = db.get(Execution, r.execution_id)
        dup = db.execute(select(Defect.key).where(Defect.test_case_id == t.id,
                                                  Defect.status.notin_(["closed", "verified"]),
                                                  Defect.approval_status != "dismissed")).scalars().all()
        project_key = t.key.split("-")[1]
        d = Defect(key=next_key(db, Defect, f"DEF-{project_key}", 4), project_id=t.project_id,
                   title=(ai.get("defect_title") or f"{t.title} fails on {ev['environment']}")[:300],
                   description=ai.get("defect_summary") or ai.get("probable_cause") or "; ".join(state["observed_facts"]),
                   severity=ai.get("recommended_severity", "high" if t.priority in ("critical", "high") else "medium"),
                   priority=ai.get("recommended_priority", "p2" if t.priority in ("critical", "high") else "p3"),
                   status="open", approval_status="recommended", requirement_id=t.requirement_id, test_case_id=t.id,
                   execution_id=ex.id, execution_result_id=r.id, expected_result=t.expected_result,
                   actual_result=r.message[:2000],
                   reproduction_steps=f"1. Select environment {ev['environment']} (Reference HCM {ex.hcm_version}).\n"
                                      f"2. Execute approved test {t.key} (script sha256 {r.script_hash}).\n"
                                      "3. Observe the assertion failure.",
                   error_log=r.stdout[-4000:], stack_trace=r.stack_trace[-8000:], ai_analysis=analysis,
                   reporter_id=state.get("actor_id"))
        db.add(d)
        db.flush()
        audit.record(db, state.get("actor_id"), "defect.recommended", "defect", d.id, d.key, d.project_id,
                     {"execution_result": r.id, "duplicates": list(dup)})
        out: ExecState = {"defect_id": d.id, "duplicate_warning": list(dup)}
        key = d.key
    # step is written after the transaction above has committed (one writer at a time in SQLite)
    tasks.step(state["run_id"], "defect_recommendation", detail={"defect": key, "duplicates": out["duplicate_warning"]},
               progress=0.8)
    return out


def human_approval(state: ExecState) -> ExecState:
    return {}


def defect_creation(state: ExecState) -> ExecState:
    with session_scope() as db:
        d = db.get(Defect, state["defect_id"])
        if state.get("decision") == "approve":
            d.approval_status = "approved"
            if d.ai_analysis:
                d.ai_analysis = {**d.ai_analysis, "confirmed": True}
        else:
            d.approval_status, d.status, d.resolved_at = "dismissed", "closed", utcnow()
    return {}


def _route_after_recommendation(state: ExecState) -> str:
    return "human_approval" if state.get("defect_id") else END


def _route_after_precheck(state: ExecState) -> str:
    return "failure_classifier" if state.get("precheck_ok") else END


def build_graph() -> StateGraph:
    g = StateGraph(ExecState)
    for n, f in [("execution_precheck", execution_precheck), ("failure_classifier", failure_classifier),
                 ("evidence_analysis", evidence_analysis), ("defect_recommendation", defect_recommendation),
                 ("human_approval", human_approval), ("defect_creation", defect_creation)]:
        g.add_node(n, f)
    g.add_edge(START, "execution_precheck")
    g.add_conditional_edges("execution_precheck", _route_after_precheck, ["failure_classifier", END])
    g.add_edge("failure_classifier", "evidence_analysis")
    g.add_edge("evidence_analysis", "defect_recommendation")
    g.add_conditional_edges("defect_recommendation", _route_after_recommendation, ["human_approval", END])
    g.add_edge("human_approval", "defect_creation")
    g.add_edge("defect_creation", END)
    return g


_compiled = None
_lock = threading.Lock()


def compiled():
    global _compiled
    with _lock:
        if _compiled is None:
            conn = sqlite3.connect(str(get_settings().checkpoint_db_path), check_same_thread=False)
            conn.execute("PRAGMA busy_timeout=10000")
            _compiled = build_graph().compile(checkpointer=SqliteSaver(conn), interrupt_before=["human_approval"])
        return _compiled


def reset_compiled() -> None:
    global _compiled
    _compiled = None


def run_failure_analysis(run_id: int, result_id: int, actor_id: int | None) -> dict[str, Any]:
    thread = {"configurable": {"thread_id": f"run-{run_id}"}}
    tasks.update_run(run_id, thread_id=f"run-{run_id}")
    final: dict[str, Any] = compiled().invoke({"result_id": result_id, "run_id": run_id, "actor_id": actor_id}, thread)
    if final.get("defect_id"):
        return {"_status": "awaiting_review", "defect_id": final["defect_id"],
                "category": final.get("category"), "duplicate_warning": final.get("duplicate_warning", [])}
    return {"category": final.get("category"), "defect_id": None,
            "_status": "completed" if final.get("ai", {}).get("status") == "ok" or not final.get("precheck_ok")
            else "degraded"}


def resume_defect_decision(run_id: int, decision: str) -> bool:
    thread = {"configurable": {"thread_id": f"run-{run_id}"}}
    snap = compiled().get_state(thread)
    if not snap.next or "human_approval" not in snap.next:
        return False
    compiled().update_state(thread, {"decision": decision})
    compiled().invoke(None, thread)
    tasks.update_run(run_id, status="completed", finished_at=utcnow(), progress=1.0,
                     message=f"Defect {decision}d by reviewer")
    return True
