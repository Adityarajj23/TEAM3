"""Restricted subprocess execution of approved pytest scripts.

Defence in depth:
  1. Scripts must pass the AST allowlist (app.guardrails.ast_validator) — rechecked here.
  2. Each run gets a fresh temporary directory containing only the scripts, a copy of the
     Reference HCM public package and a guard conftest.
  3. The child runs with an empty environment (only REFERENCE_HCM_VERSION and a minimal PATH),
     Python isolated mode (-I), no bytecode writes and no pytest cache.
  4. POSIX resource limits: address space, CPU seconds, open files, max file size, no core dumps.
  5. Network: the guard conftest disables socket creation; on Linux the child is additionally
     placed in a new network namespace when `unshare` is permitted.
  6. Hard wall-clock timeout (process group is killed) and an output-size cap.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import REPO_ROOT, get_settings
from app.guardrails.ast_validator import validate_script

GUARD_CONFTEST = '''
import socket as _socket

class _BlockedSocket(_socket.socket):
    def __init__(self, *a, **k):
        raise RuntimeError("Network access is disabled in the TraceTest sandbox")

def _blocked(*a, **k):
    raise RuntimeError("Network access is disabled in the TraceTest sandbox")

_socket.socket = _BlockedSocket
_socket.create_connection = _blocked
_socket.getaddrinfo = _blocked
'''

PLAYWRIGHT_CONFTEST = '''
import os, pytest
from playwright.sync_api import sync_playwright

TARGET_URL = os.environ.get("TRACETEST_TARGET_URL", "")
ART = os.environ.get("TRACETEST_ARTIFACT_DIR", ".")

@pytest.fixture
def base_url():
    return TARGET_URL

@pytest.fixture
def page(request):
    with sync_playwright() as p:
        exe = os.environ.get("TRACETEST_CHROMIUM_EXECUTABLE") or None
        browser = p.chromium.launch(executable_path=exe)
        pg = browser.new_page()
        logs = []
        pg.on("console", lambda m: logs.append(f"[{m.type}] {m.text}"))
        yield pg
        name = request.node.nodeid.split("::")[0].replace("/", "_").replace(".py", "")
        pg.screenshot(path=os.path.join(ART, name + ".png"))
        with open(os.path.join(ART, name + ".console.log"), "w") as fh:
            fh.write("\\n".join(logs))
        browser.close()
'''


@dataclass
class ScriptSpec:
    test_key: str
    script: str

    @property
    def file_name(self) -> str:
        return "test_" + self.test_key.replace("-", "_").lower() + ".py"

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.script.encode()).hexdigest()


@dataclass
class TestOutcome:
    test_key: str
    status: str  # passed|failed|error|skipped|timed_out|cancelled
    duration_ms: int = 0
    message: str = ""
    stack_trace: str = ""
    stdout: str = ""
    functions: int = 0


@dataclass
class SandboxResult:
    status: str  # completed | timed_out | error
    outcomes: dict[str, TestOutcome] = field(default_factory=dict)
    duration_ms: int = 0
    log: str = ""
    junit_xml: str = ""
    returncode: int | None = None
    network_namespace: bool = False
    artifact_files: list[Path] = field(default_factory=list)


def _limits(memory_mb: int | None, cpu_seconds: int):
    def apply() -> None:  # runs in the child (POSIX only)
        import resource
        os.setsid()
        limits = [(resource.RLIMIT_CPU, cpu_seconds), (resource.RLIMIT_FSIZE, 50 * 1024 * 1024),
                  (resource.RLIMIT_CORE, 0)]
        if memory_mb:  # browsers reserve large virtual address spaces, so Playwright runs skip RLIMIT_AS
            limits += [(resource.RLIMIT_AS, memory_mb * 1024 * 1024), (resource.RLIMIT_NOFILE, 256)]
        for lim, val in limits:
            try:
                resource.setrlimit(lim, (val, val))
            except (ValueError, OSError):
                pass
    return apply


_UNSHARE_OK: bool | None = None


def _unshare_available() -> bool:
    global _UNSHARE_OK
    if _UNSHARE_OK is None:
        path = shutil.which("unshare")
        if not path or not sys.platform.startswith("linux"):
            _UNSHARE_OK = False
        else:
            try:
                r = subprocess.run([path, "-rn", "true"], capture_output=True, timeout=5)
                _UNSHARE_OK = r.returncode == 0
            except Exception:
                _UNSHARE_OK = False
    return _UNSHARE_OK


def _parse_junit(xml_text: str, file_to_key: dict[str, str]) -> dict[str, TestOutcome]:
    out: dict[str, TestOutcome] = {}
    if not xml_text:
        return out
    root = ET.fromstring(xml_text)
    rank = {"passed": 0, "skipped": 1, "failed": 2, "error": 3}
    for case in root.iter("testcase"):
        classname = case.get("classname", "")
        module = classname.split(".")[0] + ".py" if classname else ""
        key = file_to_key.get(module)
        if key is None:
            continue
        status, message, trace = "passed", "", ""
        for tag in ("failure", "error", "skipped"):
            el = case.find(tag)
            if el is not None:
                status = {"failure": "failed", "error": "error", "skipped": "skipped"}[tag]
                message = el.get("message", "") or ""
                trace = el.text or ""
                break
        sysout = case.find("system-out")
        dur = int(float(case.get("time", "0") or 0) * 1000)
        prev = out.get(key)
        if prev is None:
            out[key] = TestOutcome(key, status, dur, message[:4000], trace[:20000],
                                   (sysout.text or "")[:8000] if sysout is not None else "", 1)
        else:
            prev.duration_ms += dur
            prev.functions += 1
            if rank[status] > rank[prev.status]:
                prev.status, prev.message, prev.stack_trace = status, message[:4000], trace[:20000]
    return out


def run_pytest(specs: list[ScriptSpec], hcm_version: str | None, runner: str = "pytest",
               target_url: str | None = None, timeout_s: int | None = None,
               artifact_dir: Path | None = None) -> SandboxResult:
    settings = get_settings()
    timeout_s = timeout_s or settings.exec_timeout_seconds
    allow_pw = runner == "playwright"
    file_to_key: dict[str, str] = {}
    pre_rejected: dict[str, TestOutcome] = {}

    work = Path(tempfile.mkdtemp(prefix="tt-sandbox-"))
    try:
        if runner == "pytest":
            shutil.copytree(REPO_ROOT / "reference_hcm", work / "reference_hcm",
                            ignore=shutil.ignore_patterns("__pycache__"))
            (work / "conftest.py").write_text(GUARD_CONFTEST)
        else:
            (work / "conftest.py").write_text(PLAYWRIGHT_CONFTEST)
        for spec in specs:
            report = validate_script(spec.script, allow_playwright=allow_pw)
            if not report.valid:
                pre_rejected[spec.test_key] = TestOutcome(
                    spec.test_key, "error", 0, "Rejected by AST allowlist: " + "; ".join(report.errors))
                continue
            (work / spec.file_name).write_text(spec.script)
            file_to_key[spec.file_name] = spec.test_key

        if not file_to_key:
            return SandboxResult("completed", pre_rejected, 0, "No valid scripts to execute")

        junit = work / "junit.xml"
        art = artifact_dir or (work / "artifacts")
        art.mkdir(parents=True, exist_ok=True)
        env = {"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1", "HOME": str(work),
               "PYTHONHASHSEED": "0", "LANG": "C.UTF-8"}
        if hcm_version:
            env["REFERENCE_HCM_VERSION"] = hcm_version
        if runner == "playwright":
            env["TRACETEST_TARGET_URL"] = target_url or ""
            env["TRACETEST_ARTIFACT_DIR"] = str(art)
            if settings.chromium_executable:
                env["TRACETEST_CHROMIUM_EXECUTABLE"] = str(settings.chromium_executable)
            for k in ("TRACETEST_CHROMIUM_EXECUTABLE", "PLAYWRIGHT_BROWSERS_PATH"):
                if os.environ.get(k):
                    env[k] = os.environ[k]
            env["HOME"] = os.environ.get("HOME", str(work))
        if os.name == "nt":
            env["SYSTEMROOT"] = os.environ.get("SYSTEMROOT", "")
        cmd = [sys.executable, "-I", "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-o",
               "console_output_style=classic", f"--junitxml={junit}", "--rootdir", str(work), str(work)]
        use_netns = runner == "pytest" and _unshare_available()
        if use_netns:
            cmd = [shutil.which("unshare") or "unshare", "-rn", *cmd]
        start = time.monotonic()
        popen_kw: dict = {"cwd": str(work), "env": env, "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT}
        if os.name == "posix":
            popen_kw["preexec_fn"] = _limits(settings.exec_memory_mb if runner == "pytest" else None, timeout_s + 5)
        else:
            popen_kw["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        proc = subprocess.Popen(cmd, **popen_kw)
        timed_out = False
        try:
            raw, _ = proc.communicate(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                if os.name == "posix":
                    os.killpg(proc.pid, signal.SIGKILL)
                else:
                    proc.kill()
            except ProcessLookupError:
                pass
            raw, _ = proc.communicate()
        duration = int((time.monotonic() - start) * 1000)
        cap = settings.exec_max_output_bytes
        text = (raw or b"")[:cap].decode("utf-8", "replace")
        if raw and len(raw) > cap:
            text += f"\n[output truncated at {cap} bytes]"

        junit_text = junit.read_text() if junit.exists() else ""
        outcomes = _parse_junit(junit_text, file_to_key)
        for key in file_to_key.values():
            if key not in outcomes:
                outcomes[key] = TestOutcome(key, "timed_out" if timed_out else "error", 0,
                                            "Execution timed out" if timed_out else
                                            "No result reported by pytest (collection or interpreter error)",
                                            text[-4000:])
        outcomes.update(pre_rejected)
        files = [p for p in art.glob("*") if p.is_file()] if artifact_dir else []
        status = "timed_out" if timed_out else ("completed" if junit_text else "error")
        return SandboxResult(status, outcomes, duration, text, junit_text, proc.returncode, use_netns, files)
    finally:
        shutil.rmtree(work, ignore_errors=True)
