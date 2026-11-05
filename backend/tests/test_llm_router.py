import json

import pytest

from app.llm import router
from app.llm.base import Completion, LLMProvider, ProviderError
from app.llm.providers import MockProvider
from app.llm.schemas import FailureAnalysisOut

GOOD = {"category": "application_defect", "observed_facts": ["assert 2 == 1"], "hypotheses": [],
        "probable_cause": "off by one", "suggested_actions": [], "confidence": 0.8}


class Scripted(LLMProvider):
    def __init__(self, name, outputs):
        self.name, self.model, self.outputs, self.calls = name, name + "-model", list(outputs), 0

    def configured(self):
        return True

    def complete_json(self, system, user, timeout):
        self.calls += 1
        out = self.outputs.pop(0)
        if isinstance(out, Exception):
            raise out
        return Completion(out, self.name, self.model)


@pytest.fixture(autouse=True)
def _db(app, monkeypatch):
    monkeypatch.setattr(router.time, "sleep", lambda s: None)
    router.BREAKER.failures.clear()
    router.BREAKER.opened_at.clear()


def test_repairs_invalid_json_then_succeeds():
    p = Scripted("p1", ["not json", json.dumps({"category": "bogus"}), json.dumps(GOOD)])
    res = router.generate("failure_analysis", "s", "u", FailureAnalysisOut, chain=[p])
    assert res.repairs == 2 and res.data.category == "application_defect" and p.calls == 3


def test_gives_up_after_two_repairs_without_fabricating():
    p = Scripted("p1", ["{}", "{}", "{}"])
    with pytest.raises(router.StructuredOutputError) as exc:
        router.generate("failure_analysis", "s", "u", FailureAnalysisOut, chain=[p])
    assert exc.value.raw == "{}" and p.calls == 3


def test_falls_back_on_rate_limit_and_records_traces():
    p1 = Scripted("groq", [ProviderError("429", True, 429)] * 3)
    p2 = Scripted("gemini", [json.dumps(GOOD)])
    res = router.generate("failure_analysis", "s", "fallback-test", FailureAnalysisOut, chain=[p1, p2])
    assert res.provider == "gemini" and p1.calls == 3
    from app.db.base import session_scope
    from app.db.models import ProviderTrace
    with session_scope() as db:
        statuses = [t.status for t in db.query(ProviderTrace).filter_by(provider="groq").all()]
    assert statuses.count("error") >= 3


def test_all_providers_failing_is_explicit():
    p1 = Scripted("groq", [ProviderError("bad key", False, 401)])
    with pytest.raises(router.AllProvidersFailed):
        router.generate("failure_analysis", "s", "u2", FailureAnalysisOut, chain=[p1])


def test_timeout_is_retried_then_fails_over():
    p1 = Scripted("groq", [ProviderError("Groq timeout"), ProviderError("Groq timeout"), ProviderError("Groq timeout")])
    p2 = Scripted("gemini", [json.dumps(GOOD)])
    assert router.generate("failure_analysis", "s", "u3", FailureAnalysisOut, chain=[p1, p2]).provider == "gemini"


def test_circuit_breaker_opens_after_repeated_failures():
    for _ in range(3):
        router.BREAKER.record("groq", False)
    assert router.BREAKER.is_open("groq")
    router.BREAKER.record("groq", True)
    assert not router.BREAKER.is_open("groq")


def test_no_silent_mock_in_live_mode(monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "llm_mode", "live")
    monkeypatch.setattr(get_settings(), "groq_api_key", None)
    monkeypatch.setattr(get_settings(), "gemini_api_key", None)
    assert router.provider_chain() == []
    assert not any(isinstance(p, MockProvider) for p in router.provider_chain())
    with pytest.raises(router.NoProviderConfigured):
        router.generate("failure_analysis", "s", "u", FailureAnalysisOut)
    st = router.provider_status()
    assert st["any_configured"] is False and all(not p["configured"] for p in st["providers"])
    assert "key" not in json.dumps(st).lower().replace("any_configured", "")


def test_slot_pool_rotation_and_auth_invalidation():
    from app.llm.providers import SlotPool

    pool = SlotPool(["secret-alpha-123456", "secret-beta-789012"], "groq")
    assert pool.configured()
    candidates = pool.get_candidate_slots()
    assert len(candidates) == 2

    # Key 1 fails with 401 Unauthorized -> marked invalid
    pool.record_failure(candidates[0], is_auth=True)
    assert candidates[0].state == "invalid"

    # Only Key 2 remains available
    remaining = pool.get_candidate_slots()
    assert len(remaining) == 1
    assert remaining[0].slot_id == 2

    # Key 2 fails with 429 Rate Limit -> marked rate_limited
    pool.record_failure(remaining[0], is_rate_limit=True, retry_after=100.0)
    assert remaining[0].state == "rate_limited"

    # No candidate slots available during cooldown
    assert len(pool.get_candidate_slots()) == 0

    st = pool.status()
    assert len(st) == 2
    assert "key" not in json.dumps(st).lower()

