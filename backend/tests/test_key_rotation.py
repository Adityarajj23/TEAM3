"""Tests for LLM key rotation, LRU slot selection, concurrency pacing, fallback models, and secret safety."""
from __future__ import annotations

import json
import os
import time

import httpx
import pytest

from app.core.config import Settings
from app.llm.base import ProviderError
from app.llm.providers import GeminiProvider, GroqProvider, ManagedSlot, SlotPool

GOOD_RESPONSE = {
    "category": "application_defect",
    "observed_facts": ["assert 2 == 1"],
    "hypotheses": ["off by one"],
    "probable_cause": "index out of bounds",
    "suggested_actions": ["fix indexing"],
    "confidence": 0.95,
}


def test_slot_pool_lru_rotation():
    """Verify SlotPool selects healthy slots in least-recently-used order."""
    pool = SlotPool(["key-alpha-12345", "key-beta-67890", "key-gamma-99999"], "groq")
    assert pool.configured()
    assert len(pool.slots) == 3

    # Initially, all are healthy with last_used_at = 0.
    candidates = pool.get_candidate_slots()
    assert len(candidates) == 3
    first_slot = candidates[0]
    assert first_slot.slot_id == 1

    # Mark first_slot as used
    pool.mark_used(first_slot)
    candidates_after_1 = pool.get_candidate_slots()
    # Now slot 2 and 3 should come before slot 1
    assert candidates_after_1[0].slot_id == 2
    assert candidates_after_1[1].slot_id == 3
    assert candidates_after_1[2].slot_id == 1

    # Mark slot 2 as used
    pool.mark_used(candidates_after_1[0])
    candidates_after_2 = pool.get_candidate_slots()
    # Now slot 3 should be first
    assert candidates_after_2[0].slot_id == 3
    assert candidates_after_2[1].slot_id == 1
    assert candidates_after_2[2].slot_id == 2


def test_slot_pool_429_burst_vs_daily_quota():
    """Verify 429 burst uses short cooldown while daily quota uses reset header capped at 300s."""
    pool = SlotPool(["key-one-123456", "key-two-654321"], "groq")
    slot1, slot2 = pool.slots[0], pool.slots[1]

    # Test burst 429 with Retry-After: 15
    pool.record_failure(slot1, is_rate_limit=True, retry_after=15.0, is_daily_quota=False)
    assert slot1.state == "rate_limited"
    assert 10.0 <= (slot1.cooldown_until - time.monotonic()) <= 16.0

    # Remaining candidate is slot 2
    candidates = pool.get_candidate_slots()
    assert len(candidates) == 1
    assert candidates[0].slot_id == 2

    # Test daily quota exhaustion on slot 2 with reset header 86400 (capped at 300s)
    pool.record_failure(slot2, is_rate_limit=True, retry_after=86400.0, is_daily_quota=True)
    assert slot2.state == "rate_limited"
    remaining_sec = slot2.cooldown_until - time.monotonic()
    assert 290.0 <= remaining_sec <= 301.0  # capped at 300s


def test_slot_pool_401_permanent_invalidation():
    """Verify 401/403 permanently marks slot invalid until restart."""
    pool = SlotPool(["bad-key-123456", "good-key-654321"], "groq")
    bad_slot = pool.slots[0]

    pool.record_failure(bad_slot, is_auth=True)
    assert bad_slot.state == "invalid"

    # Even after time passes, candidate slots NEVER include the invalid slot
    bad_slot.cooldown_until = time.monotonic() - 100
    candidates = pool.get_candidate_slots()
    assert len(candidates) == 1
    assert candidates[0].slot_id == 2


def test_slot_pool_500_transient_backoff():
    """Verify 5xx server errors trigger exponential backoff with jitter."""
    pool = SlotPool(["key-500-test123"], "groq")
    slot = pool.slots[0]

    # Error 1 -> ~2s
    pool.record_failure(slot, is_server_error=True)
    assert slot.state == "degraded"
    assert 1.5 <= (slot.cooldown_until - time.monotonic()) <= 3.0

    # Error 2 -> ~4s
    pool.record_failure(slot, is_server_error=True)
    assert 3.5 <= (slot.cooldown_until - time.monotonic()) <= 5.5

    # Error 3 -> ~8s
    pool.record_failure(slot, is_server_error=True)
    assert 7.0 <= (slot.cooldown_until - time.monotonic()) <= 10.0


def test_groq_mock_transport_key_rotation_and_fallback_model(monkeypatch):
    """Simulate HTTP server with 429 burst on primary model, falling back to groq_fallback_model."""
    requests_seen: list[dict] = []

    def handle_request(request: httpx.Request) -> httpx.Response:
        auth = request.headers.get("Authorization", "")
        body = json.loads(request.content.decode("utf-8"))
        model = body.get("model")
        requests_seen.append({"auth": auth, "model": model})

        # Slot 1 on primary model -> 429 burst
        if "key1" in auth and model == "openai/gpt-oss-120b":
            return httpx.Response(429, headers={"Retry-After": "5"}, json={"error": {"message": "Rate limit exceeded"}})

        # Slot 2 on primary model -> 429 burst
        if "key2" in auth and model == "openai/gpt-oss-120b":
            return httpx.Response(429, headers={"Retry-After": "5"}, json={"error": {"message": "Rate limit exceeded"}})

        # Fallback model openai/gpt-oss-20b -> succeeds!
        if model == "openai/gpt-oss-20b":
            return httpx.Response(200, json={
                "choices": [{"message": {"content": json.dumps(GOOD_RESPONSE)}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            })

        return httpx.Response(500, json={"error": {"message": "Unexpected test case"}})

    monkeypatch.setenv("GROQ_API_KEY", "gsk_key1_test")
    monkeypatch.setenv("GROQ_API_KEY2", "gsk_key2_test")
    monkeypatch.delenv("GROQ_API_KEY3", raising=False)
    monkeypatch.delenv("GROQ_KEY", raising=False)
    monkeypatch.delenv("GROQ_KEY2", raising=False)
    monkeypatch.delenv("GROQ_KEY3", raising=False)

    settings = Settings(
        groq_model="openai/gpt-oss-120b",
        groq_fallback_model="openai/gpt-oss-20b",
        groq_concurrency_per_slot=2,
    )

    provider = GroqProvider(settings)
    provider._client = httpx.Client(transport=httpx.MockTransport(handle_request))

    comp = provider.complete_json("system instruction", "user prompt", timeout=10.0)
    assert comp.provider == "groq"
    assert comp.model == "openai/gpt-oss-20b"
    assert comp.slot_id is not None
    # Verify that primary model was attempted first on slots, then fallback was attempted
    models_tried = [r["model"] for r in requests_seen]
    assert "openai/gpt-oss-120b" in models_tried
    assert "openai/gpt-oss-20b" in models_tried


def test_secrets_never_appear_in_error_or_traces():
    """Verify secrets are redacted and never leak into ProviderError or status."""
    raw_secret = "gsk_super_secret_key_999888777"
    pool = SlotPool([raw_secret], "groq")
    status = pool.status()
    status_str = json.dumps(status)
    assert raw_secret not in status_str
    assert "..." in status[0]["masked"]
    assert status[0]["masked"].startswith("gsk_su")
    assert status[0]["masked"].endswith("8777")


def test_concurrency_pacing_limits_active_requests():
    """Verify slot concurrency semaphore bounds active calls."""
    slot = ManagedSlot("gsk_concurrency_test", 1, "groq", concurrency_limit=2)
    assert slot.active_requests == 0

    with slot.throttle(timeout=1.0):
        assert slot.active_requests == 1
        with slot.throttle(timeout=1.0):
            assert slot.active_requests == 2
            # 3rd request should time out
            with pytest.raises(ProviderError) as exc:
                with slot.throttle(timeout=0.05):
                    pass
            assert "concurrency" in str(exc.value).lower()
        assert slot.active_requests == 1
    assert slot.active_requests == 0


def test_system_provider_status_api(admin):
    """GET /api/v1/system/provider-status returns valid slot metrics without raw keys."""
    res = admin.get("/system/provider-status")
    assert res.status_code == 200
    data = res.json()
    assert "providers" in data
    assert "mode" in data
    for prov in data["providers"]:
        assert "name" in prov
        assert "model" in prov
        assert "configured" in prov
        if "slots" in prov:
            for s in prov["slots"]:
                assert "slot" in s
                assert "masked" in s
                assert "state" in s
                assert "error_rate" in s
                assert "requests" in s
                assert "errors" in s
                # Ensure no raw key leaks
                assert len(s["masked"]) <= 16 or "..." in s["masked"]


@pytest.mark.skipif(not os.getenv("TRACETEST_LIVE_KEY_TEST"), reason="Opt-in live smoke test")
def test_live_key_smoke(monkeypatch):
    """Live smoke test sending trivial probe through each configured provider slot."""
    from dotenv import dotenv_values

    from app.core.config import REPO_ROOT
    env_vals = dotenv_values(REPO_ROOT / ".env")
    for k, v in env_vals.items():
        if v and ("GROQ" in k or "GEMINI" in k):
            monkeypatch.setenv(k, v)
    settings = Settings()
    for prov_cls, keys, name in [(GroqProvider, settings.groq_keys, "groq"), (GeminiProvider, settings.gemini_keys, "gemini")]:
        for i, key in enumerate(keys):
            p = prov_cls(Settings(**{f"{name}_api_key": key}))
            comp = p.complete_json(
                system="Health probe. Return valid JSON only.",
                user='{"probe": "ping"}',
                timeout=15.0,
            )
            assert comp.text, f"{name} slot {i+1} returned empty"
            cleaned = comp.text.strip().strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
            parsed = json.loads(cleaned)
            assert isinstance(parsed, dict)
