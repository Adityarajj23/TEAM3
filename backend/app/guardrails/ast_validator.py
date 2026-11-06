"""AST allowlist validation of generated pytest scripts before they can be approved or executed."""
from __future__ import annotations

import ast
from dataclasses import dataclass, field

BASE_ALLOWED = {
    "pytest", "decimal", "datetime", "math", "re", "json", "dataclasses", "typing", "fractions",
}
HCM_ALLOWED = {
    "reference_hcm", "reference_hcm.payroll", "reference_hcm.attendance", "reference_hcm.leave",
    "reference_hcm.eligibility", "reference_hcm.approvals",
}
REAL_SUT_ALLOWED = {
    "boto3", "boto3.dynamodb.conditions", "moto", "moto.dynamodb", "jose",
}
SIMULATION_ALLOWED = {
    "echobox_harness", "echobox_harness.backend", "echobox_harness.table",
}
ALLOWED_IMPORTS = BASE_ALLOWED | HCM_ALLOWED | REAL_SUT_ALLOWED | SIMULATION_ALLOWED
PLAYWRIGHT_IMPORTS = {"playwright", "playwright.sync_api"}
FORBIDDEN_MODULES = {
    "os", "sys", "subprocess", "socket", "shutil", "urllib", "requests", "http",
    "ftplib", "smtplib", "xmlrpc", "ctypes", "posix", "pty", "commands", "importlib",
    "pickle", "shelve", "builtins", "signal", "multiprocessing", "threading",
}
FORBIDDEN_NAMES = {
    "open", "eval", "exec", "compile", "__import__", "__builtins__", "globals", "locals", "vars", "getattr", "setattr",
    "delattr", "input", "breakpoint", "exit", "quit", "memoryview", "help",
}
FORBIDDEN_ATTRS = {"__class__", "__bases__", "__subclasses__", "__globals__", "__builtins__", "__dict__",
                   "__code__", "__mro__", "__getattribute__", "__loader__", "__spec__"}
MAX_SCRIPT_BYTES = 40_000


@dataclass
class ValidationReport:
    valid: bool
    errors: list[str] = field(default_factory=list)
    test_functions: list[str] = field(default_factory=list)


def validate_script(source: str, allow_playwright: bool = False, env_kind: str = "real_code") -> ValidationReport:
    errors: list[str] = []
    if not source or not source.strip():
        return ValidationReport(False, ["Script is empty"])
    if len(source.encode()) > MAX_SCRIPT_BYTES:
        return ValidationReport(False, [f"Script exceeds {MAX_SCRIPT_BYTES} bytes"])
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return ValidationReport(False, [f"SyntaxError: {exc.msg} (line {exc.lineno})"])

    if env_kind == "simulation":
        allowed = BASE_ALLOWED | HCM_ALLOWED | SIMULATION_ALLOWED
    elif env_kind in ("real_code", "platform_run", "default"):
        allowed = BASE_ALLOWED | HCM_ALLOWED | REAL_SUT_ALLOWED
    else:  # generic / python_lib
        allowed = BASE_ALLOWED
    if allow_playwright:
        allowed |= PLAYWRIGHT_IMPORTS

    def is_mod_allowed(mod_name: str) -> bool:
        if env_kind == "python_lib":
            # In python_lib, allow project modules and base modules while strictly banning system/network/exec modules
            if any(mod_name == f or mod_name.startswith(f + ".") for f in FORBIDDEN_MODULES):
                return False
            if mod_name.startswith("_"):
                return False
            return True
        return mod_name in allowed

    tests: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if not is_mod_allowed(alias.name):
                    errors.append(f"Import of '{alias.name}' is not allowed (line {node.lineno})")
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if node.level or not is_mod_allowed(mod):
                errors.append(f"Import from '{mod or '.'}' is not allowed (line {node.lineno})")
            for alias in node.names:
                if alias.name == "*":
                    errors.append(f"Wildcard import is not allowed (line {node.lineno})")
        elif isinstance(node, ast.Name) and (node.id in FORBIDDEN_NAMES or (node.id.startswith("__") and node.id.endswith("__"))):
            errors.append(f"Use of '{node.id}' is not allowed (line {node.lineno})")
        elif isinstance(node, ast.Attribute):
            if node.attr in FORBIDDEN_ATTRS or (node.attr.startswith("__") and node.attr.endswith("__")):
                errors.append(f"Access to attribute '{node.attr}' is not allowed (line {node.lineno})")
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            errors.append(f"global/nonlocal statements are not allowed (line {node.lineno})")
        elif isinstance(node, (ast.AsyncFunctionDef, ast.Await)):
            errors.append(f"async code is not allowed (line {node.lineno})")
        elif isinstance(node, ast.While):
            errors.append(f"while loops are not allowed (line {node.lineno})")
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            tests.append(node.name)
    # top-level statements: imports, defs, simple constant assignments, docstrings
    for stmt in tree.body:
        if not isinstance(stmt, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.ClassDef, ast.Assign,
                                 ast.AnnAssign, ast.Expr)):
            errors.append(f"Top-level statement '{type(stmt).__name__}' is not allowed (line {stmt.lineno})")
        if isinstance(stmt, ast.Expr) and not isinstance(stmt.value, ast.Constant):
            errors.append(f"Top-level expressions are not allowed (line {stmt.lineno})")
    if not tests:
        errors.append("Script defines no test_* function")
    return ValidationReport(not errors, sorted(set(errors), key=errors.index), tests)


def validate_test_syntax(source: str, env_kind: str = "real_code", allow_playwright: bool = False) -> tuple[bool, list[str]]:
    """Validates test syntax against allowlist for the given environment kind."""
    rep = validate_script(source, allow_playwright=allow_playwright, env_kind=env_kind)
    return rep.valid, rep.errors
