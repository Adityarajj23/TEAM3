"""Concrete providers: Groq (OpenAI-compatible), Gemini (official SDK), Ollama, Mock."""
from __future__ import annotations

import json

import httpx

from app.core.config import Settings
from app.llm.base import Completion, LLMProvider, ProviderError


class GroqProvider(LLMProvider):
    name = "groq"

    def __init__(self, s: Settings):
        self.key, self.model, self.base = s.groq_api_key, s.groq_model, s.groq_base_url.rstrip("/")

    def configured(self) -> bool:
        return bool(self.key)

    def complete_json(self, system: str, user: str, timeout: float) -> Completion:
        try:
            r = httpx.post(f"{self.base}/chat/completions", timeout=timeout,
                           headers={"Authorization": f"Bearer {self.key}"},
                           json={"model": self.model, "temperature": 0.1,
                                 "response_format": {"type": "json_object"},
                                 "messages": [{"role": "system", "content": system},
                                              {"role": "user", "content": user}]})
        except httpx.TimeoutException as exc:
            raise ProviderError(f"Groq timeout: {exc}") from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"Groq transport error: {exc}") from exc
        if r.status_code == 429:
            raise ProviderError("Groq rate limited (HTTP 429)", True, 429)
        if r.status_code >= 500:
            raise ProviderError(f"Groq server error HTTP {r.status_code}", True, r.status_code)
        if r.status_code >= 400:
            raise ProviderError(f"Groq rejected request HTTP {r.status_code}: {r.text[:300]}", False, r.status_code)
        data = r.json()
        usage = data.get("usage") or {}
        return Completion(data["choices"][0]["message"]["content"] or "", self.name, self.model,
                          usage.get("prompt_tokens"), usage.get("completion_tokens"))


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, s: Settings):
        self.key, self.model = s.gemini_api_key, s.gemini_model

    def configured(self) -> bool:
        return bool(self.key)

    def complete_json(self, system: str, user: str, timeout: float) -> Completion:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:  # pragma: no cover
            raise ProviderError("google-genai SDK not installed", False) from exc
        try:
            client = genai.Client(api_key=self.key, http_options={"timeout": int(timeout * 1000)})
            resp = client.models.generate_content(
                model=self.model, contents=user,
                config=types.GenerateContentConfig(system_instruction=system, temperature=0.1,
                                                   response_mime_type="application/json"))
        except Exception as exc:  # SDK raises various error types
            msg = str(exc)
            status = 429 if "429" in msg or "RESOURCE_EXHAUSTED" in msg else None
            raise ProviderError(f"Gemini error: {msg[:300]}", True, status) from exc
        usage = getattr(resp, "usage_metadata", None)
        return Completion(resp.text or "", self.name, self.model,
                          getattr(usage, "prompt_token_count", None), getattr(usage, "candidates_token_count", None))


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
