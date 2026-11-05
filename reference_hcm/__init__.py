"""Reference HCM Engine — a deterministic, fictional HCM system under test.

The active build is selected by the ``REFERENCE_HCM_VERSION`` environment
variable ("1.0" = QA build with documented faults, "1.1" = fix candidate).
Tests import the public API only::

    from reference_hcm import payroll, attendance, leave, eligibility, approvals
"""
from __future__ import annotations

import importlib
import os

SUPPORTED_VERSIONS = ("1.0", "1.1")
VERSION = os.environ.get("REFERENCE_HCM_VERSION", "1.1")
if VERSION not in SUPPORTED_VERSIONS:
    raise ValueError(f"Unsupported REFERENCE_HCM_VERSION {VERSION!r}")

_pkg = "reference_hcm.v" + VERSION.replace(".", "_")
payroll = importlib.import_module(_pkg + ".payroll")
attendance = importlib.import_module(_pkg + ".attendance")
leave = importlib.import_module(_pkg + ".leave")
eligibility = importlib.import_module(_pkg + ".eligibility")
approvals = importlib.import_module(_pkg + ".approvals")

__all__ = ["VERSION", "payroll", "attendance", "leave", "eligibility", "approvals"]
