from app.execution.sandbox import ScriptSpec, run_pytest

OT = ScriptSpec("TC-T-0001", "from reference_hcm import payroll\n\n\ndef test_ot():\n"
                             "    assert payroll.calculate_overtime_hours(40, 40) == 0\n")


def test_v10_fault_detected_and_v11_passes():
    r10 = run_pytest([OT], "1.0")
    r11 = run_pytest([OT], "1.1")
    assert r10.outcomes["TC-T-0001"].status == "failed"
    assert "assert 1 == 0" in r10.outcomes["TC-T-0001"].message
    assert r11.outcomes["TC-T-0001"].status == "passed"


def test_unsafe_script_rejected_before_execution():
    bad = ScriptSpec("TC-T-0002", "import os\n\ndef test_x():\n    os.system('id')\n")
    r = run_pytest([bad], "1.1")
    assert r.outcomes["TC-T-0002"].status == "error"
    assert "AST allowlist" in r.outcomes["TC-T-0002"].message


def test_timeout_is_enforced():
    slow = ScriptSpec("TC-T-0003", "def test_spin():\n    total = 0\n    for i in range(10 ** 12):\n        total += i\n")
    r = run_pytest([slow], "1.1", timeout_s=3)
    assert r.status == "timed_out"
    assert r.outcomes["TC-T-0003"].status == "timed_out"


def test_output_is_capped(monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "exec_max_output_bytes", 500)
    noisy = ScriptSpec("TC-T-0004", "def test_noise():\n    for i in range(5000):\n        print('x' * 50)\n"
                                    "    assert False\n")
    r = run_pytest([noisy], "1.1")
    assert "[output truncated at 500 bytes]" in r.log
