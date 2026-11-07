#!/usr/bin/env python3
"""Workforce Management Quality Project (WFMQ) End-to-End Workflow Demonstration.

Executes the complete 38-step requirements-based quality engineering lifecycle:
1. Requirements-Based Project Creation (WFMQ).
2. Deep Project Context & Role Configuration.
3. Multi-Document Ingestion (PRD, SRS, Business Rules) with granular ExtractedContent persistence.
4. Grounded Requirement Extraction with explicit provenance (explicit_documented, user_provided, ai_inferred).
5. Ambiguity & Multi-Document Contradiction Detection (Overtime Multiplier 1.5x vs 2.0x, Leave Probation 90d vs 30d).
6. Human Review, Clarification Resolution, and Dual-Control Approvals.
7. Structured Given/When/Then Acceptance Criteria Generation (AC1, AC2).
8. Comprehensive Test Scenario Generation across all 10 categories.
9. Deterministic Specification Validation (VAL-*).
10. Behaviour Simulation (SIM-*) with Blocked Hardware Detection & Automated Defect Generation (DEF-WFMQ-*).
11. Bidirectional Traceability Matrix generation.
12. 19-Section Comprehensive Quality Report Export (JSON + HTML).
13. Persistence Verification across full SQLite database reconnection.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

# Add backend to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from sqlalchemy import delete, select
from app.db.base import SessionLocal, utcnow
from app.db.models import (
    AcceptanceCriterion,
    Defect,
    Document,
    Environment,
    Execution,
    ExecutionResult,
    ExtractedContent,
    Organisation,
    Project,
    ProjectContext,
    ProjectRole,
    Requirement,
    RequirementClarification,
    TestCase,
    User,
)
from app.services.document_processor import process_document, save_document_file, validate_file_upload
from app.services.requirement_intelligence import analyze_and_extract_project_requirements
from app.services.requirements_dashboard import (
    generate_comprehensive_quality_report,
    generate_quality_report_html,
    get_project_traceability_matrix,
    get_requirements_project_dashboard_data,
)
from app.services.simulation_engine import run_behaviour_simulation, run_specification_validation
from app.services.test_design import (
    generate_acceptance_criteria_for_project,
    generate_test_scenarios_for_project,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("wfmq_demo")


def run_wfmq_demonstration():
    print("=" * 80)
    print(" TRACETEST AI — WFMQ END-TO-END DEMONSTRATION & PERSISTENCE VERIFICATION")
    print("=" * 80)

    db = SessionLocal()
    try:
        # Step 1: Ensure default org & admin user exist
        org = db.execute(select(Organisation)).scalars().first()
        if not org:
            org = Organisation(name="Default Org", key="DEF")
            db.add(org)
            db.flush()

        admin = db.execute(select(User).where(User.email == "admin@dayforce.com")).scalars().first()
        if not admin:
            admin = db.execute(select(User)).scalars().first()

        admin_id = admin.id if admin else None

        # Step 2: Clean up any previous WFMQ project for deterministic run
        existing_proj = db.execute(select(Project).where(Project.key == "WFMQ")).scalars().first()
        if existing_proj:
            log.info("Cleaning up prior WFMQ demonstration project (ID: %d)...", existing_proj.id)
            db.delete(existing_proj)
            db.commit()

        # Step 3: Create Requirements-Based Project 'WFMQ'
        log.info("Step 1/13: Creating Requirements-Based Project 'WFMQ'...")
        project = Project(
            key="WFMQ",
            name="Workforce Management Quality Project",
            description="Enterprise workforce management platform supporting scheduling, timecard compliance, premium overtime calculations, and labor audit governance.",
            status="active",
            project_type="requirements_based",
            business_domain="Enterprise HR / Workforce Management",
            product_type="Enterprise Cloud SaaS",
            business_goal="Automate employee scheduling, real-time punch capture, overtime calculations, and statutory labor law compliance.",
            owner_name="Sohan HR Tech Quality Lead",
            team="Core Quality Engineering",
            version="1.0.0",
            environment_name="Simulation (WFMQ Deterministic)",
            target_users_and_roles=[
                "Employee",
                "Team Lead",
                "Department Manager",
                "Payroll Administrator",
                "Compliance Auditor",
            ],
            objectives=[
                "100% accurate gross pay and premium overtime calculation",
                "Zero silent validation failures on timecard punch intervals",
                "Deterministic traceability from statutory regulations to automated test verification",
            ],
            business_scenarios=[
                "Employee records daily shift hours with mandatory meal break deduction",
                "Department manager reviews and approves weekly timecard submissions before payroll cut-off",
            ],
            functional_expectations=[
                "System shall require multi-factor authentication for Payroll Administrator accounts",
                "System shall reject punch-out timestamps that precede punch-in timestamps with HTTP 400 Bad Request",
            ],
            non_functional_expectations=[
                "Sub-second API response time for punch-in requests",
                "Complete tamper-evident audit logging on wage adjustments",
            ],
            constraints_and_assumptions=[
                "Workweek runs Monday 00:00:00 through Sunday 23:59:59",
                "Base currency fixed to USD ($)",
            ],
            explicit_exclusions=[
                "Direct automated ACH clearing house dispatch is handled by third-party banking integration",
            ],
            organisation_id=org.id,
            owner_id=admin_id,
        )
        db.add(project)
        db.flush()
        log.info("Project created: ID=%d, Key=%s, Name='%s'", project.id, project.key, project.name)

        # Step 4: Create Default Simulation Environment
        env = Environment(
            project_id=project.id,
            name="Simulation (WFMQ Deterministic)",
            kind="simulation",
            base_url="http://127.0.0.1:8000/simulation/wfmq",
            is_default=True,
        )
        db.add(env)

        # Step 5: Configure Project Roles
        roles_data = [
            ("Employee", "Standard workforce member", ["timecard.submit", "timecard.view_self", "leave.request"], "Record shift hours and submit absence requests", "Cannot view peer records or approve timecards"),
            ("Department Manager", "Operational supervisor", ["timecard.approve", "timecard.view_team", "leave.approve"], "Review shift logs, approve overtime, and supervise schedules", "Cannot alter payroll wage configuration"),
            ("Payroll Administrator", "Financial operations specialist", ["payroll.calculate", "payroll.export", "wage.adjust", "audit.view"], "Execute gross-to-net payroll runs and process wage adjustments", "Must provide dual-authorization for manual overrides"),
            ("Compliance Auditor", "Statutory auditor", ["audit.view", "report.generate", "compliance.inspect"], "Review historical labor logs and audit trails", "Read-only access to all operational data"),
        ]
        for r_name, r_desc, r_perms, r_resp, r_restr in roles_data:
            db.add(ProjectRole(
                project_id=project.id,
                role_name=r_name,
                description=r_desc,
                permissions=r_perms,
                responsibilities=r_resp,
                restrictions=r_restr,
            ))

        # Step 6: Create Deep Project Context
        proj_context = ProjectContext(
            project_id=project.id,
            product_overview="Unified workforce management system managing labor scheduling, timecard approvals, statutory meal breaks, and overtime calculations.",
            problem_statement="Manual timesheet processes introduce compliance risks, meal break violations, and payroll calculation errors.",
            target_users=["Employee", "Department Manager", "Payroll Administrator", "Compliance Auditor"],
            product_modules=["Employee Management", "Time & Attendance", "Leave Management", "Payroll Calculation", "RBAC"],
            architecture_context="Cloud-native microservices backend with asynchronous payroll calculation engine and deterministic simulation models.",
            technical_stack={"runtime": "Python 3.11 / FastAPI", "database": "SQLite 3 WAL", "frontend": "React 19 / TypeScript / Vite"},
            external_integrations=["Workday HCM Core API", "Kronos Kiosk Hardware", "ADP Payroll Export"],
            business_rules=[
                "Overtime calculation threshold: 40 hours per calendar workweek",
                "Mandatory meal break: minimum 30 minutes for shifts over 6 hours",
                "Quarter-hour punch rounding threshold: standard 7-minute window",
            ],
            security_expectations="All API endpoints require cryptographically verified JWT Bearer tokens; session inactivity timeout of 15 minutes.",
            privacy_requirements="Employee PII and wage details encrypted at rest using AES-256.",
            performance_expectations="Clock-in endpoint latency p95 < 250ms under peak shift transitions.",
            availability_expectations="99.95% system uptime during operational workweek hours.",
            regulatory_standards=["FLSA 29 U.S.C. § 207", "California Labor Code § 510", "SOC 2 Type II"],
            assumptions=["Employees clock in via authenticated web browser or biometric terminal."],
            exclusions=["Automated tax withholding calculations deferred to external payroll provider."],
            dependencies=["FastAPI backend service", "Database storage volume", "Auth provider"],
        )
        db.add(proj_context)
        db.commit()

        # Step 7: Ingest 3 Real Documents with Granular ExtractedContent Persistence
        docs_dir = REPO_ROOT / "data" / "wfmq_sample_docs"
        sample_files = [
            ("wfmq_prd.md", "prd", "WFMQ Product Requirements Document", "Product Requirements Document (PRD)"),
            ("wfmq_srs.md", "srs", "WFMQ Software Requirements Specification", "Software Requirements Specification (SRS)"),
            ("wfmq_business_rules.md", "business_rules", "WFMQ Statutory Business Rules & Payroll Policy", "Business Rules Specification"),
        ]

        uploaded_docs: list[Document] = []
        log.info("Step 2/13: Ingesting and parsing 3 specification documents...")
        for fname, purpose, disp_name, desc in sample_files:
            fpath = docs_dir / fname
            content_bytes = fpath.read_bytes()
            safe_name, ftype, fsize = validate_file_upload(fname, content_bytes)

            doc = Document(
                project_id=project.id,
                filename=safe_name,
                display_name=disp_name,
                file_path="",  # will be set after saving
                file_type=ftype,
                document_type=purpose,
                file_size_bytes=fsize,
                purpose=purpose,
                description=desc,
                version="1.0",
                owner="Sohan HR Tech Quality Lead",
                priority="high",
                status="uploaded",
            )
            db.add(doc)
            db.flush()

            saved_path, checksum = save_document_file(project.id, doc.id, safe_name, content_bytes)
            doc.file_path = str(saved_path)
            doc.checksum = checksum
            db.commit()

            # Process document: parsing, section extraction, and ExtractedContent persistence
            processed_doc = process_document(db, doc.id)
            uploaded_docs.append(processed_doc)

            # Verify ExtractedContent records
            ec_count = db.execute(
                select(ExtractedContent).where(ExtractedContent.document_id == doc.id)
            ).scalars().all()
            log.info("Document ingested: '%s' (ID=%d, Chars=%d, ExtractedContent records=%d)",
                     doc.filename, doc.id, len(processed_doc.extracted_text), len(ec_count))

        # Step 8: Execute Requirement Intelligence Analysis (Provenance + Ambiguities + Contradictions)
        log.info("Step 3/13: Analyzing requirements, detecting ambiguities and multi-document contradictions...")
        analysis_res = analyze_and_extract_project_requirements(db, project.id, author_id=admin_id)
        log.info("Analysis Result: Extracted=%d (Explicit=%d, User-Provided=%d, Inferred=%d, Clarifications Opened=%d)",
                 analysis_res["total_extracted"],
                 analysis_res["explicit_documented"],
                 analysis_res["user_provided"],
                 analysis_res["ai_inferred"],
                 analysis_res["clarifications_opened"])

        # Verify Contradictions Detected
        contradictions = db.execute(
            select(RequirementClarification).where(
                RequirementClarification.project_id == project.id,
                RequirementClarification.type == "contradiction"
            )
        ).scalars().all()
        log.info("Contradictions identified across documents: %d", len(contradictions))
        for c in contradictions:
            log.info("  [CONTRADICTION DETECTED] %s: %s", c.question, c.impact)

        # Step 9: Review & Approve Requirements; Resolve 1 Clarification
        log.info("Step 4/13: Performing dual-control requirement review and approvals...")
        all_reqs = db.execute(select(Requirement).where(Requirement.project_id == project.id)).scalars().all()
        for r in all_reqs:
            r.review_status = "approved"
            r.status = "approved"

        # Resolve one open ambiguity clarification
        ambig = db.execute(
            select(RequirementClarification).where(
                RequirementClarification.project_id == project.id,
                RequirementClarification.type != "contradiction",
                RequirementClarification.status == "open"
            )
        ).scalars().first()
        if ambig:
            ambig.status = "resolved"
            ambig.user_response = "Resolved: Maximum acceptable clock-in processing latency is 250 milliseconds with deterministic HTTP 400 error payloads."
            ambig.resolved_at = utcnow()
            log.info("Resolved clarification #%d: '%s'", ambig.id, ambig.question[:60])
        db.commit()

        # Step 10: Generate Structured Given/When/Then Acceptance Criteria
        log.info("Step 5/13: Generating Acceptance Criteria (Given/When/Then, AC1, AC2)...")
        ac_res = generate_acceptance_criteria_for_project(db, project.id, author_id=admin_id)
        log.info("Generated %d acceptance criteria for %d requirements.", ac_res["created_count"], len(all_reqs))

        # Step 11: Generate Comprehensive Test Cases across all 10 categories
        log.info("Step 6/13: Generating Test Scenarios across 10 categories...")
        tc_res = generate_test_scenarios_for_project(db, project.id, author_id=admin_id)
        log.info("Generated %d test specifications.", tc_res["created_count"])

        # Add explicit biometric hardware scenario to demonstrate BLOCKED capability
        bio_req = next((r for r in all_reqs if "biometric" in (r.title + (r.evidence_excerpt or "")).lower()), all_reqs[0])
        bio_test = TestCase(
            key="WFMQ-TC-BIO01",
            project_id=project.id,
            requirement_id=bio_req.id,
            requirement_version=1,
            clause_keys=[f"{bio_req.key}.C1"],
            ac_keys=[f"{bio_req.key}.AC1"],
            title="Verify physical biometric fingerprint clock-in terminal synchronization",
            description="Validate offline punch buffer synchronization from physical optical biometric reader kiosks.",
            preconditions="Physical biometric fingerprint reader hardware device is wired to kiosk terminal.",
            test_data={"device_type": "optical_fingerprint_reader", "terminal_id": "KIOSK-042"},
            expected_result="Kiosk reads fingerprint biometric template and uploads punch record to cloud API.",
            priority="high",
            test_type="functional",
            test_category="integration",
            execution_capability="hardware",
            approval_status="approved",
            generation_provenance="manual",
            steps_json=[
                {"step": 1, "action": "Present enrolled fingerprint to optical scanner", "expected": "Hardware reads biometric minutiae"},
                {"step": 2, "action": "Transmit punch payload to cloud endpoint", "expected": "Punch recorded with 201 Created"},
            ],
            confidence=0.98,
            status="approved",
            version=1,
        )
        db.add(bio_test)
        db.commit()

        # Step 12: Run Specification Validation (VAL-*)
        log.info("Step 7/13: Running Specification Validation (VAL-*)...")
        val_exec = run_specification_validation(db, project.id, user_id=admin_id)
        log.info("Specification Validation Run: Key=%s, Status=%s, Total=%d, Passed=%d, Failed=%d, Duration=%dms",
                 val_exec.key, val_exec.status, val_exec.total, val_exec.passed, val_exec.failed, val_exec.duration_ms)

        # Step 13: Run Behaviour Simulation (SIM-*) with Contradiction Defect Logging
        log.info("Step 8/13: Running Behaviour Simulation (SIM-*)...")
        sim_exec = run_behaviour_simulation(db, project.id, user_id=admin_id)
        log.info("Behaviour Simulation Run: Key=%s, Status=%s, Total=%d, Passed=%d, Failed=%d, Blocked/Skipped=%d, Duration=%dms",
                 sim_exec.key, sim_exec.status, sim_exec.total, sim_exec.passed, sim_exec.failed, sim_exec.skipped, sim_exec.duration_ms)

        # Step 14: Inspect Generated Defects
        defects = db.execute(
            select(Defect).where(Defect.project_id == project.id).order_by(Defect.created_at.desc())
        ).scalars().all()
        log.info("Step 9/13: Inspecting logged defects (%d total):", len(defects))
        for d in defects:
            log.info("  [%s] %s (Severity: %s, Status: %s, ResultID: %s)",
                     d.key, d.title[:70], d.severity, d.status, d.execution_result_id)

        # Step 15: Retrieve Bidirectional Traceability Matrix
        log.info("Step 10/13: Compiling Bidirectional Traceability Matrix...")
        trace_matrix = get_project_traceability_matrix(db, project.id)
        cov_pct = round((trace_matrix["covered_requirements"] / max(1, trace_matrix["total_requirements"])) * 100, 1)
        log.info("Traceability Summary: Total Reqs=%d, Covered Reqs=%d (%.1f%% coverage)",
                 trace_matrix["total_requirements"],
                 trace_matrix["covered_requirements"],
                 cov_pct)

        # Step 16: Generate 19-Section Comprehensive Quality Engineering Report
        log.info("Step 11/13: Generating 19-Section Quality Engineering Report...")
        report_json = generate_comprehensive_quality_report(db, project.id)
        report_html = generate_quality_report_html(db, project.id)

        # Save HTML report to disk for inspection
        html_out_path = REPO_ROOT / "docs" / "WFMQ_QUALITY_REPORT.html"
        html_out_path.write_text(report_html, encoding="utf-8")
        log.info("HTML Quality Report written to: %s (Size: %d bytes)", html_out_path, len(report_html))

        # Step 17: Query Requirements Project Dashboard
        log.info("Step 12/13: Querying Requirements Project Dashboard...")
        dashboard_data = get_requirements_project_dashboard_data(db, project.id)
        log.info("Dashboard Metrics: %s", json.dumps({
            "documents": dashboard_data["documents_summary"]["total"],
            "requirements": dashboard_data["requirements_summary"]["total"],
            "test_cases": dashboard_data["test_design_summary"]["total_tests"],
            "sim_runs": dashboard_data["execution_summary"]["simulation_runs"],
            "val_runs": dashboard_data["execution_summary"]["specification_validation_runs"],
            "open_defects": len(defects),
        }, indent=2))

        db.close()

        # Step 18: Full Database Persistence Verification (Clean Reconnect)
        log.info("Step 13/13: Testing clean SQLite reconnect and verifying 100% persistence...")
        db2 = SessionLocal()
        try:
            p_check = db2.get(Project, project.id)
            assert p_check is not None, "Project lost on reconnect!"
            assert p_check.key == "WFMQ"
            assert p_check.project_type == "requirements_based"

            doc_check = db2.execute(select(Document).where(Document.project_id == project.id)).scalars().all()
            assert len(doc_check) == 3, f"Expected 3 documents, found {len(doc_check)}"

            ec_check = db2.execute(
                select(ExtractedContent).join(Document).where(Document.project_id == project.id)
            ).scalars().all()
            assert len(ec_check) >= 6, f"Expected granular ExtractedContent, found {len(ec_check)}"

            req_check = db2.execute(select(Requirement).where(Requirement.project_id == project.id)).scalars().all()
            assert len(req_check) >= 5, f"Expected extracted requirements, found {len(req_check)}"

            ac_check = db2.execute(
                select(AcceptanceCriterion).join(Requirement).where(Requirement.project_id == project.id)
            ).scalars().all()
            assert len(ac_check) >= 10, f"Expected acceptance criteria, found {len(ac_check)}"

            tc_check = db2.execute(select(TestCase).where(TestCase.project_id == project.id)).scalars().all()
            assert len(tc_check) >= 50, f"Expected test cases across 10 categories, found {len(tc_check)}"

            exec_check = db2.execute(select(Execution).where(Execution.project_id == project.id)).scalars().all()
            assert len(exec_check) == 2, f"Expected 2 executions (1 VAL, 1 SIM), found {len(exec_check)}"

            defect_check = db2.execute(select(Defect).where(Defect.project_id == project.id)).scalars().all()
            assert len(defect_check) >= 1, f"Expected logged defects from simulation discrepancy, found {len(defect_check)}"

            print("=" * 80)
            print(" SUCCESS: WFMQ END-TO-END DEMONSTRATION & PERSISTENCE VERIFIED 100%!")
            print(f"  - Project ID: {p_check.id} ({p_check.key})")
            print(f"  - Ingested Documents: {len(doc_check)}")
            print(f"  - Extracted Content Chunks: {len(ec_check)}")
            print(f"  - Grounded Requirements: {len(req_check)}")
            print(f"  - Acceptance Criteria: {len(ac_check)}")
            print(f"  - Test Cases (10 Categories): {len(tc_check)}")
            print(f"  - Executions: {len(exec_check)} ({[e.key for e in exec_check]})")
            print(f"  - Defects Logged: {len(defect_check)} ({[d.key for d in defect_check]})")
            print(f"  - Quality Report: docs/WFMQ_QUALITY_REPORT.html ({len(report_html)} bytes)")
            print("=" * 80)
        finally:
            db2.close()

    except Exception:
        log.exception("WFMQ Demonstration failed!")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_wfmq_demonstration()
