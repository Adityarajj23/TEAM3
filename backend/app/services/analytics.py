"""Database-derived quality metrics, traceability and reports. No hardcoded figures."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.db.models import Clause, Defect, Execution, ExecutionResult, Project, Requirement, RequirementVersion, TestCase

ACTIVE_TEST = ("pending_review", "approved", "changes_requested", "needs_reapproval")


def _current_clauses(db: Session, project_ids: list[int]) -> list[tuple[Clause, Requirement]]:
    q = (select(Clause, Requirement).join(RequirementVersion, RequirementVersion.id == Clause.version_id)
         .join(Requirement, and_(Requirement.id == Clause.requirement_id,
                                 Requirement.current_version == RequirementVersion.version))
         .where(Requirement.project_id.in_(project_ids or [-1]), Requirement.status != "deprecated")
         .order_by(Requirement.key, Clause.position))
    return list(db.execute(q).tuples().all())


def _latest_results(db: Session, test_ids: list[int]) -> dict[int, ExecutionResult]:
    if not test_ids:
        return {}
    sub = (select(ExecutionResult.test_case_id, func.max(ExecutionResult.id).label("mid"))
           .where(ExecutionResult.test_case_id.in_(test_ids)).group_by(ExecutionResult.test_case_id).subquery())
    rows = db.execute(select(ExecutionResult).join(sub, ExecutionResult.id == sub.c.mid)).scalars()
    return {r.test_case_id: r for r in rows}


def coverage_by_project(db: Session, project_ids: list[int]) -> list[dict]:
    clauses = _current_clauses(db, project_ids)
    tests = db.execute(select(TestCase.project_id, TestCase.requirement_id, TestCase.clause_keys)
                       .where(TestCase.project_id.in_(project_ids or [-1]),
                              TestCase.status.in_(ACTIVE_TEST))).all()
    covered: dict[int, set[str]] = defaultdict(set)
    for _pid, rid, keys in tests:
        covered[rid].update(keys)
    per: dict[int, list[int]] = defaultdict(lambda: [0, 0])
    for c, r in clauses:
        per[r.project_id][0] += 1
        per[r.project_id][1] += 1 if c.clause_key in covered[r.id] else 0
    names = dict(db.execute(select(Project.id, Project.key).where(Project.id.in_(project_ids or [-1]))).tuples().all())
    return [{"project_id": pid, "project": names.get(pid), "total_clauses": t, "covered_clauses": cv,
             "coverage_pct": round(100 * cv / t, 1) if t else 0.0} for pid, (t, cv) in sorted(per.items())]


def dashboard(db: Session, project_ids: list[int], date_from: datetime | None, date_to: datetime | None) -> dict:
    date_to = date_to or utcnow() + timedelta(days=1)
    date_from = date_from or date_to - timedelta(days=120)
    pids = project_ids or [-1]
    projects = db.execute(select(Project).where(Project.id.in_(pids))).scalars().all()
    reqs = db.execute(select(Requirement.status, func.count()).where(Requirement.project_id.in_(pids))
                      .group_by(Requirement.status)).tuples().all()
    req_counts = dict(reqs)
    test_counts = dict(db.execute(select(TestCase.status, func.count()).where(TestCase.project_id.in_(pids))
                                  .group_by(TestCase.status)).tuples().all())
    ex_filter = and_(Execution.project_id.in_(pids), Execution.started_at >= date_from, Execution.started_at < date_to)
    executions = db.execute(select(Execution).where(ex_filter).order_by(Execution.started_at)).scalars().all()
    res_counts = dict(db.execute(select(ExecutionResult.status, func.count())
                                 .join(Execution, Execution.id == ExecutionResult.execution_id)
                                 .where(ex_filter).group_by(ExecutionResult.status)).tuples().all())
    denom = sum(res_counts.get(s, 0) for s in ("passed", "failed", "error", "timed_out"))
    pass_rate = round(100 * res_counts.get("passed", 0) / denom, 1) if denom else None
    defects = db.execute(select(Defect).where(Defect.project_id.in_(pids), Defect.approval_status == "approved")).scalars().all()
    open_defects = [d for d in defects if d.status not in ("verified", "closed")]
    cov = coverage_by_project(db, [p.id for p in projects])
    tot = sum(c["total_clauses"] for c in cov)
    cvd = sum(c["covered_clauses"] for c in cov)

    trend: dict[str, Counter] = defaultdict(Counter)
    for e in executions:
        wk = (e.started_at - timedelta(days=e.started_at.weekday())).strftime("%Y-%m-%d")
        trend[wk]["passed"] += e.passed
        trend[wk]["failed"] += e.failed
        trend[wk]["error"] += e.errored
        trend[wk]["executions"] += 1
    resolution: dict[str, Counter] = defaultdict(Counter)
    for d in defects:
        resolution[(d.created_at - timedelta(days=d.created_at.weekday())).strftime("%Y-%m-%d")]["opened"] += 1
        if d.resolved_at:
            resolution[(d.resolved_at - timedelta(days=d.resolved_at.weekday())).strftime("%Y-%m-%d")]["resolved"] += 1
    recent_changes = db.execute(
        select(RequirementVersion, Requirement).join(Requirement, Requirement.id == RequirementVersion.requirement_id)
        .where(Requirement.project_id.in_(pids), RequirementVersion.version > 1)
        .order_by(RequirementVersion.created_at.desc()).limit(8)).all()
    per_project = []
    for p in projects:
        pe = [e for e in executions if e.project_id == p.id]
        pd = [d for d in open_defects if d.project_id == p.id]
        p_res = sum(e.passed for e in pe), sum(e.passed + e.failed + e.errored for e in pe)
        c = next((x for x in cov if x["project_id"] == p.id), None)
        per_project.append({"project_id": p.id, "key": p.key, "name": p.name, "status": p.status,
                            "executions": len(pe), "pass_rate": round(100 * p_res[0] / p_res[1], 1) if p_res[1] else None,
                            "open_defects": len(pd), "critical_defects": sum(1 for d in pd if d.severity == "critical"),
                            "coverage_pct": c["coverage_pct"] if c else 0.0})
    return {
        "filters": {"project_ids": project_ids, "date_from": date_from.isoformat(), "date_to": date_to.isoformat()},
        "kpis": {
            "total_projects": len(projects), "active_projects": sum(1 for p in projects if p.status == "active"),
            "total_requirements": sum(req_counts.values()),
            "analysed_requirements": sum(v for k, v in req_counts.items() if k in ("analysed", "approved", "changed")),
            "total_test_cases": sum(test_counts.values()), "approved_test_cases": test_counts.get("approved", 0),
            "pending_reviews": test_counts.get("pending_review", 0) + test_counts.get("needs_reapproval", 0),
            "total_executions": len(executions), "pass_rate": pass_rate,
            "failed_executions": sum(1 for e in executions if e.status in ("failed", "error", "timed_out")),
            "open_defects": len(open_defects), "critical_defects": sum(1 for d in open_defects if d.severity == "critical"),
            "requirement_coverage": round(100 * cvd / tot, 1) if tot else 0.0,
        },
        "charts": {
            "execution_trend": [{"week": k, **v} for k, v in sorted(trend.items())],
            "result_distribution": [{"status": k, "count": v} for k, v in sorted(res_counts.items())],
            "coverage_by_project": cov,
            "defect_severity": [{"severity": s, "count": sum(1 for d in open_defects if d.severity == s)}
                                for s in ("critical", "high", "medium", "low")],
            "defect_resolution": [{"week": k, "opened": v["opened"], "resolved": v["resolved"]}
                                  for k, v in sorted(resolution.items())],
            "test_status": [{"status": k, "count": v} for k, v in sorted(test_counts.items())],
        },
        "recent_changes": [{"requirement_id": r.id, "key": r.key, "title": v.title, "version": v.version,
                            "summary": v.change_summary, "at": v.created_at.isoformat()} for v, r in recent_changes],
        "recent_executions": [{"id": e.id, "key": e.key, "status": e.status, "source": e.source,
                               "passed": e.passed, "failed": e.failed, "errored": e.errored,
                               "hcm_version": e.hcm_version, "started_at": e.started_at.isoformat() if e.started_at else None}
                              for e in sorted(executions, key=lambda e: e.started_at or utcnow(), reverse=True)[:8]],
        "projects": per_project,
    }


def traceability(db: Session, project_ids: list[int], requirement_id: int | None = None) -> dict:
    rows = _current_clauses(db, project_ids)
    if requirement_id:
        rows = [(c, r) for c, r in rows if r.id == requirement_id]
    req_ids = {r.id for _, r in rows}
    tq = select(TestCase).where(TestCase.project_id.in_(project_ids or [-1]), TestCase.status != "deprecated")
    if requirement_id:
        tq = tq.where(TestCase.requirement_id == requirement_id)
    tests = list(db.execute(tq.order_by(TestCase.key)).scalars())
    latest = _latest_results(db, [t.id for t in tests])
    clause_index = {(r.id, c.clause_key): i for i, (c, r) in enumerate(rows)}
    test_cols, cells = [], []
    covered: set[int] = set()
    orphans, duplicates, impacted = [], [], []
    for t in tests:
        lr = latest.get(t.id)
        state = {"approved": "approved", "pending_review": "pending_approval", "changes_requested": "needs_review",
                 "needs_reapproval": "needs_review", "rejected": "rejected"}.get(t.status, t.status)
        if lr and lr.status in ("failed", "error", "timed_out") and t.status == "approved":
            state = "failed_execution"
        elif lr and lr.status == "passed" and t.status == "approved":
            state = "passed"
        idxs = [clause_index[(t.requirement_id, k)] for k in t.clause_keys if (t.requirement_id, k) in clause_index]
        if t.requirement_id in req_ids and not idxs:
            orphans.append(t.key)
        if t.duplicate_of:
            duplicates.append(t.key)
        if t.status == "needs_reapproval":
            impacted.append(t.key)
        if not idxs:
            continue
        col = len(test_cols)
        test_cols.append({"id": t.id, "key": t.key, "title": t.title, "status": t.status, "state": state,
                          "test_type": t.test_type, "last_result": lr.status if lr else None,
                          "last_execution_id": lr.execution_id if lr else None})
        for i in idxs:
            cells.append([i, col, state])
            if t.status in ACTIVE_TEST:
                covered.add(i)
    clauses_out = [{"index": i, "requirement_id": r.id, "requirement_key": r.key, "clause_key": c.clause_key,
                    "text": c.text, "covered": i in covered, "ambiguous": bool(c.ambiguity_flags)}
                   for i, (c, r) in enumerate(rows)]
    total = len(rows)
    return {"clauses": clauses_out, "tests": test_cols, "cells": cells,
            "summary": {"total_clauses": total, "covered_clauses": len(covered), "untested_clauses": total - len(covered),
                        "coverage_pct": round(100 * len(covered) / total, 1) if total else 0.0,
                        "orphan_tests": orphans, "duplicate_tests": duplicates, "impacted_tests": impacted}}


def quality_report(db: Session, project_ids: list[int]) -> dict:
    now = utcnow()
    projects = db.execute(select(Project).where(Project.id.in_(project_ids or [-1]))).scalars().all()
    out = []
    for p in projects:
        reqs = db.scalar(select(func.count()).select_from(Requirement).where(Requirement.project_id == p.id)) or 0
        tests = db.execute(select(TestCase).where(TestCase.project_id == p.id, TestCase.status != "deprecated")).scalars().all()
        defects = db.execute(select(Defect).where(Defect.project_id == p.id, Defect.approval_status == "approved")).scalars().all()
        open_d = [d for d in defects if d.status not in ("verified", "closed")]
        ageing = Counter()
        for d in open_d:
            age = (now - d.created_at).days
            ageing["0-7d" if age <= 7 else "8-30d" if age <= 30 else "31-90d" if age <= 90 else ">90d"] += 1
        execs = db.execute(select(Execution).where(Execution.project_id == p.id).order_by(Execution.started_at)).scalars().all()
        # regression: tests whose latest result failed after a previous pass
        hist: dict[int, list[str]] = defaultdict(list)
        for tc_id, st in db.execute(select(ExecutionResult.test_case_id, ExecutionResult.status)
                                    .join(Execution, Execution.id == ExecutionResult.execution_id)
                                    .where(Execution.project_id == p.id).order_by(Execution.started_at)).all():
            hist[tc_id].append(st)
        regressions = sum(1 for seq in hist.values() if len(seq) >= 2 and seq[-1] == "failed" and "passed" in seq[:-1])
        automated = sum(1 for t in tests if t.automation in ("pytest", "playwright"))
        last = execs[-1] if execs else None
        cov = coverage_by_project(db, [p.id])
        out.append({
            "project": p.key, "name": p.name, "requirements": reqs, "tests": len(tests),
            "approved_tests": sum(1 for t in tests if t.status == "approved"),
            "automation_coverage_pct": round(100 * automated / len(tests), 1) if tests else 0.0,
            "requirement_coverage_pct": cov[0]["coverage_pct"] if cov else 0.0,
            "defect_density_per_requirement": round(len(defects) / reqs, 2) if reqs else 0.0,
            "open_defects": len(open_d), "critical_open": sum(1 for d in open_d if d.severity == "critical"),
            "defect_ageing": dict(ageing), "regressions": regressions,
            "impacted_tests": sum(1 for t in tests if t.status == "needs_reapproval"),
            "executions": len(execs),
            "last_execution": {"key": last.key, "status": last.status, "hcm_version": last.hcm_version,
                               "passed": last.passed, "failed": last.failed} if last else None,
            "release_readiness": ("blocked" if any(d.severity == "critical" for d in open_d) else
                                  "at_risk" if open_d or (last and last.status != "passed") else "ready"),
        })
    return {"generated_at": now.isoformat(), "projects": out}
