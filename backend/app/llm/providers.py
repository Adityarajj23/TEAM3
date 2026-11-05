"""Concrete providers: Groq (OpenAI-compatible), Gemini (official SDK), Ollama, Mock.
Supports multi-credential rotation, rate-limit cooldown, and auth invalidation.
"""
from __future__ import annotations

import json
import threading
import time

import httpx

from app.core.config import Settings
from app.llm.base import Completion, LLMProvider, ProviderError


class ManagedSlot:
    def __init__(self, secret: str, slot_id: int, provider: str):
        self.secret = secret.strip()
        self.slot_id = slot_id
        self.provider = provider
        self.masked = (self.secret[:6] + "..." + self.secret[-4:]) if len(self.secret) > 10 else "***"
        self.state = "healthy"  # healthy | rate_limited | invalid
        self.cooldown_until: float = 0.0
        self.consecutive_errors: int = 0
        self.total_requests: int = 0
        self.total_errors: int = 0


class SlotPool:
    def __init__(self, secrets: list[str], provider: str):
        self.provider = provider
        self.slots = [ManagedSlot(s, i + 1, provider) for i, s in enumerate(secrets) if s and s.strip()]
        self._lock = threading.Lock()

    def configured(self) -> bool:
        return len(self.slots) > 0

    def get_candidate_slots(self) -> list[ManagedSlot]:
        now = time.monotonic()
        with self._lock:
            for s in self.slots:
                if s.state == "rate_limited" and now >= s.cooldown_until:
                    s.state = "healthy"
                    s.cooldown_until = 0.0
            return [s for s in self.slots if s.state == "healthy"]

    def record_success(self, slot: ManagedSlot) -> None:
        with self._lock:
            slot.state = "healthy"
            slot.consecutive_errors = 0
            slot.cooldown_until = 0.0
            slot.total_requests += 1

    def record_failure(self, slot: ManagedSlot, is_auth: bool = False, is_rate_limit: bool = False,
                       retry_after: float | None = None) -> None:
        with self._lock:
            slot.total_requests += 1
            slot.total_errors += 1
            slot.consecutive_errors += 1
            now = time.monotonic()
            if is_auth:
                slot.state = "invalid"
            elif is_rate_limit:
                slot.state = "rate_limited"
                cooldown = retry_after if (retry_after and retry_after > 0) else 60.0
                slot.cooldown_until = now + cooldown
            else:
                if slot.consecutive_errors >= 3:
                    slot.state = "rate_limited"
                    slot.cooldown_until = now + 30.0

    def status(self) -> list[dict]:
        now = time.monotonic()
        with self._lock:
            return [{
                "slot": s.slot_id,
                "masked": s.masked,
                "state": s.state,
                "cooldown_sec": max(0, int(s.cooldown_until - now)) if s.state == "rate_limited" else 0,
                "requests": s.total_requests,
                "errors": s.total_errors,
            } for s in self.slots]


class GroqProvider(LLMProvider):
    name = "groq"

    def __init__(self, s: Settings):
        self.keys = s.groq_keys
        self.key = self.keys[0] if self.keys else s.groq_api_key
        self.pool = SlotPool(self.keys, self.name)
        self.model = s.groq_model
        self.base = s.groq_base_url.rstrip("/")

    def configured(self) -> bool:
        return self.pool.configured()

    def slot_status(self) -> list[dict]:
        return self.pool.status()

    def complete_json(self, system: str, user: str, timeout: float) -> Completion:
        candidates = self.pool.get_candidate_slots()
        if not candidates:
            raise ProviderError("All Groq credentials are unavailable, rate limited, or invalid", True, 429)

        errors: list[str] = []
        for slot in candidates:
            try:
                r = httpx.post(f"{self.base}/chat/completions", timeout=timeout,
                               headers={"Authorization": f"Bearer {slot.secret}"},
                               json={"model": self.model, "temperature": 0.1,
                                     "max_tokens": 4096,
                                     "response_format": {"type": "json_object"},
                                     "messages": [{"role": "system", "content": system},
                                                  {"role": "user", "content": user}]})
            except httpx.TimeoutException as exc:
                self.pool.record_failure(slot, is_rate_limit=False)
                errors.append(f"Slot {slot.slot_id} timeout: {exc}")
                continue
            except httpx.HTTPError as exc:
                self.pool.record_failure(slot, is_rate_limit=False)
                errors.append(f"Slot {slot.slot_id} transport: {exc}")
                continue

            if r.status_code in (401, 403):
                self.pool.record_failure(slot, is_auth=True)
                errors.append(f"Slot {slot.slot_id} auth rejected HTTP {r.status_code}")
                continue
            if r.status_code == 429:
                retry_after_hdr = r.headers.get("Retry-After")
                retry_after_sec = float(retry_after_hdr) if retry_after_hdr and retry_after_hdr.isdigit() else 60.0
                self.pool.record_failure(slot, is_rate_limit=True, retry_after=retry_after_sec)
                errors.append(f"Slot {slot.slot_id} rate limited HTTP 429")
                continue
            if r.status_code >= 500:
                self.pool.record_failure(slot, is_rate_limit=False)
                errors.append(f"Slot {slot.slot_id} server error HTTP {r.status_code}")
                continue
            if r.status_code >= 400:
                if "json_validate_failed" in r.text:
                    self.pool.record_failure(slot, is_rate_limit=True, retry_after=10.0)
                    errors.append(f"Slot {slot.slot_id} json_validate_failed HTTP 400")
                    continue
                self.pool.record_failure(slot, is_rate_limit=False)
                raise ProviderError(f"Groq rejected request HTTP {r.status_code}: {r.text[:300]}", False, r.status_code)

            data = r.json()
            usage = data.get("usage") or {}
            self.pool.record_success(slot)
            return Completion(data["choices"][0]["message"]["content"] or "", self.name, self.model,
                              usage.get("prompt_tokens"), usage.get("completion_tokens"))

        raise ProviderError(f"Groq failover failed: {' | '.join(errors)}", True, 429)


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, s: Settings):
        self.keys = s.gemini_keys
        self.key = self.keys[0] if self.keys else s.gemini_api_key
        self.pool = SlotPool(self.keys, self.name)
        # 2.0-flash is shut down upstream in favor of 2.5-flash / 3.8-flash
        self.model = "gemini-2.5-flash" if s.gemini_model == "gemini-2.0-flash" else s.gemini_model

    def configured(self) -> bool:
        return self.pool.configured()

    def slot_status(self) -> list[dict]:
        return self.pool.status()

    def complete_json(self, system: str, user: str, timeout: float) -> Completion:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:  # pragma: no cover
            raise ProviderError("google-genai SDK not installed", False) from exc

        candidates = self.pool.get_candidate_slots()
        if not candidates:
            raise ProviderError("All Gemini credentials are unavailable, rate limited, or invalid", True, 429)

        errors: list[str] = []
        for slot in candidates:
            try:
                client = genai.Client(api_key=slot.secret, http_options={"timeout": int(timeout * 1000)})
                resp = client.models.generate_content(
                    model=self.model, contents=user,
                    config=types.GenerateContentConfig(system_instruction=system, temperature=0.1,
                                                       response_mime_type="application/json"))
                usage = getattr(resp, "usage_metadata", None)
                self.pool.record_success(slot)
                return Completion(resp.text or "", self.name, self.model,
                                  getattr(usage, "prompt_token_count", None), getattr(usage, "candidates_token_count", None))
            except Exception as exc:
                msg = str(exc)
                is_auth = any(x in msg for x in ("401", "403", "API_KEY_INVALID", "PERMISSION_DENIED"))
                is_rate = any(x in msg for x in ("429", "RESOURCE_EXHAUSTED", "quota"))
                self.pool.record_failure(slot, is_auth=is_auth, is_rate_limit=is_rate)
                errors.append(f"Slot {slot.slot_id} error: {msg[:200]}")
                continue

        raise ProviderError(f"Gemini failover failed: {' | '.join(errors)}", True, 429)


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, s: Settings):
        self.base, self.model = (s.ollama_base_url or "").rstrip("/"), s.ollama_model

    def configured(self) -> bool:
        return bool(self.base)

    def complete_json(self, system: str, user: str, timeout: float) -> Completion:
        try:
            r = httpx.post(f"{self.base}/api/chat", timeout=timeout, json={
                "model": self.model, "stream": False, "format": "json",
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
            r.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"Ollama error: {exc}") from exc
        return Completion(r.json().get("message", {}).get("content", ""), self.name, self.model)


class MockProvider(LLMProvider):
    """Deterministic fixture provider. ONLY active when TRACETEST_LLM_MODE=mock (tests/CI)."""
    name = "mock"
    model = "fixture-v1"

    def __init__(self, responder=None):
        from app.llm.mock_fixtures import respond
        self.responder = responder or respond

    def configured(self) -> bool:
        return True

    def complete_json(self, system: str, user: str, timeout: float) -> Completion:
        return Completion(json.dumps(self.responder(system, user)), self.name, self.model)
