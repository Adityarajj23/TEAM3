"""Domain enumerations and state machines (deterministic)."""
from __future__ import annotations

ROLES = {
    "admin": "Full administrative access to all projects and settings",
    "qa_engineer": "Author requirements and tests, execute suites, manage defects",
    "reviewer": "Review and approve generated tests and defect recommendations",
}

# role -> permissions
PERMISSIONS: dict[str, set[str]] = {
    "admin": {"*"},
    "qa_engineer": {"project.read", "requirement.write", "requirement.analyse", "test.write", "suite.write",
                    "suite.execute", "execution.read", "defect.write", "defect.transition", "export.read",
                    "eval.run", "integration.read", "audit.read"},
    "reviewer": {"project.read", "test.review", "defect.approve", "defect.transition", "execution.read",
                 "export.read", "integration.read", "audit.read"},
}

TEST_TYPES = ("functional", "positive", "negative", "boundary", "regression", "security", "compliance", "integration")
PRIORITIES = ("critical", "high", "medium", "low")
SEVERITIES = ("critical", "high", "medium", "low")
DEFECT_PRIORITIES = ("p1", "p2", "p3", "p4")
FAILURE_CATEGORIES = ("application_defect", "test_automation_defect", "configuration_issue", "environment_failure",
                      "data_validation_failure", "permission_issue", "timeout", "unknown")

DEFECT_TRANSITIONS: dict[str, set[str]] = {
    "open": {"triaged", "closed"},
    "triaged": {"assigned", "closed"},
    "assigned": {"in_progress", "triaged"},
    "in_progress": {"fixed", "assigned"},
    "fixed": {"ready_for_retest", "reopened"},
    "ready_for_retest": {"verified", "reopened"},
    "verified": {"closed", "reopened"},
    "closed": {"reopened"},
    "reopened": {"triaged", "assigned", "in_progress"},
}

TEST_REVIEW_DECISIONS = ("approve", "reject", "request_changes")
EXECUTABLE_TEST_STATUS = "approved"


def can_transition_defect(current: str, target: str) -> bool:
    return target in DEFECT_TRANSITIONS.get(current, set())


def has_permission(roles: set[str], perm: str) -> bool:
    for r in roles:
        perms = PERMISSIONS.get(r, set())
        if "*" in perms or perm in perms:
            return True
    return False
