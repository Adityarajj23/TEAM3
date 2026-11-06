#!/usr/bin/env python3
"""Diagnostic Doctor Script for TraceTest AI.

Checks Python, Node.js, Git, Bubblewrap sandbox, Playwright Chromium,
database readiness, and environment variable configuration (names only).
Prints an authoritative pass/fail health table.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

# Add backend to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))


def check_python() -> tuple[bool, str]:
    ver = sys.version_info
    v_str = f"{ver.major}.{ver.minor}.{ver.micro}"
    ok = ver.major == 3 and ver.minor >= 10
    return ok, f"Python {v_str} ({sys.executable})"


def check_node() -> tuple[bool, str]:
    node = shutil.which("node")
    if not node:
        return False, "node binary not found in PATH"
    try:
        r = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=5)
        return r.returncode == 0, f"Node {r.stdout.strip()}"
    except Exception as e:
        return False, str(e)


def check_git() -> tuple[bool, str]:
    git = shutil.which("git")
    if not git:
        return False, "git binary not found in PATH"
    try:
        r = subprocess.run([git, "--version"], capture_output=True, text=True, timeout=5)
        return r.returncode == 0, r.stdout.strip()
    except Exception as e:
        return False, str(e)


def check_bwrap() -> tuple[bool, str]:
    bwrap = shutil.which("bwrap")
    if not bwrap:
        return False, "bubblewrap binary not found"
    try:
        true_bin = shutil.which("true") or "/bin/true"
        cmd = [bwrap, "--unshare-all", "--ro-bind", "/usr", "/usr"]
        for d in ["/bin", "/lib", "/lib64"]:
            p = Path(d)
            if p.is_symlink():
                cmd.extend(["--symlink", os.readlink(d), d])
            elif p.exists():
                cmd.extend(["--ro-bind", d, d])
        cmd.extend(["--proc", "/proc", "--dev", "/dev", true_bin])
        r = subprocess.run(cmd, capture_output=True, timeout=5)
        if r.returncode == 0:
            return True, f"bwrap available (kernel user namespaces active: {bwrap})"
        return False, f"bwrap returned code {r.returncode}: {r.stderr.decode()[:100]}"
    except Exception as e:
        return False, str(e)


def check_playwright() -> tuple[bool, str]:
    chrome = shutil.which("chromium") or shutil.which("google-chrome")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=chrome, headless=True)
            b.close()
        return True, f"Chromium headless available ({chrome or 'managed browser'})"
    except Exception as e:
        return False, f"Playwright launch failed: {e}"


def check_database() -> tuple[bool, str]:
    try:
        from app.db.base import get_engine
        from sqlalchemy import text
        eng = get_engine()
        with eng.connect() as conn:
            r = conn.execute(text("SELECT count(*) FROM projects")).scalar()
            return True, f"SQLite connected ({r} projects recorded)"
    except Exception as e:
        return False, f"Database error: {e}"


def check_environment() -> tuple[bool, str]:
    try:
        from app.core.config import get_settings
        from app.llm.providers import GeminiProvider, GroqProvider
        s = get_settings()
        groq = GroqProvider(s)
        gemini = GeminiProvider(s)
        groq_slots = len(groq.pool.slots)
        gemini_slots = len(gemini.pool.slots)
        return True, f"Valid config (env={s.app_env}, Groq slots={groq_slots}, Gemini slots={gemini_slots})"
    except Exception as e:
        return False, f"Configuration invalid: {e}"


def main() -> int:
    print("=" * 68)
    print(" TraceTest AI System Health & Readiness Doctor")
    print("=" * 68)

    checks = [
        ("Python Runtime (>=3.10)", check_python),
        ("Node.js Runtime", check_node),
        ("Git Client", check_git),
        ("Bubblewrap Sandbox (bwrap)", check_bwrap),
        ("Playwright Chromium Browser", check_playwright),
        ("Database & Schema Readiness", check_database),
        ("Environment & Key Slots", check_environment),
    ]

    all_passed = True
    print(f"{'Component':<32} | {'Status':<8} | {'Details'}")
    print("-" * 32 + "-+-" + "-" * 8 + "-+-" + "-" * 24)

    for name, fn in checks:
        ok, details = fn()
        status_str = "PASS" if ok else "FAIL"
        if not ok:
            all_passed = False
        print(f"{name:<32} | {status_str:<8} | {details}")

    print("=" * 68)
    if all_passed:
        print("ALL SYSTEM CHECKS PASSED: Environment ready for production QA workflows.")
        return 0
    else:
        print("WARNING: One or more checks failed. Review details above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
