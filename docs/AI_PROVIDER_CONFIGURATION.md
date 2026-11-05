# AI Provider Configuration & Key Management — TraceTest AI

## 1. Multi-Provider Architecture

TraceTest AI implements a fault-tolerant multi-provider AI architecture designed to survive vendor rate limits, outages, and quota exhaustion:

1. **Primary High-Speed Live Engine**: **Groq** (`openai/gpt-oss-120b`) via OpenAI-compatible REST API.
2. **Secondary Multimodal Live Engine**: **Gemini** (`gemini-2.5-flash`) via official Google GenAI SDK.
3. **Local Private Fallback Engine**: **Ollama** (`llama3.1`) for air-gapped or offline development.

---

## 2. Multi-Key Slot Pool & Circuit Breakers

To maximize throughput and prevent 429 throttling from stalling production QA workflows, each provider is backed by a **Slot Pool** managing up to three independent credentials:

```
Provider: Groq
  - Slot 1: GROQ_KEY / GROQ_API_KEY
  - Slot 2: GROQ_KEY2 / GROQ_API_KEY2
  - Slot 3: GROQ_KEY3 / GROQ_API_KEY3

Provider: Gemini
  - Slot 1: GEMINI_KEY / GEMINI_API_KEY
  - Slot 2: GEMINI_KEY2 / GEMINI_API_KEY2
  - Slot 3: GEMINI_KEY3 / GEMINI_API_KEY3
```

### Circuit Breaker Dynamics
- **State: Closed**: Slot is healthy and receives requests.
- **State: Open**: Triggered when a slot experiences 3 consecutive failures (network timeouts, 500 server errors, or 429 quota exhaustion).
- **Cooldown**: Slot remains in cooldown for 60 seconds (or follows upstream `Retry-After` header value) before entering half-open state for a test attempt.
- **Failover Sequence**: If Slot 1 encounters rate limits, the request immediately fails over to Slot 2, then Slot 3, before cascading to the secondary provider (Gemini).

---

## 3. Real-World Failure Observation: Gemini Free Tier Quota Exhaustion

During the empirical evaluation benchmark on EchoBox scenarios, the system encountered the following real-world event:
- Groq (`openai/gpt-oss-120b`) executed 16 LLM generation calls across 4 scenarios with **100% schema pass rate** and **0 errors**.
- Gemini (`gemini-2.5-flash`) processed initial requests before hitting Google Free Tier quota:
  ```
  ClientError: 429 RESOURCE_EXHAUSTED. Quota exceeded for metric:
  generativelanguage.googleapis.com/generate_content_free_tier_requests,
  limit: 20 per day. Please retry in 12h29m.
  ```
- **Observed Failover Behavior**: The Slot Pool marked Gemini Slot 1 as rate limited, evaluated candidate slots, discovered the shared free-tier project quota exhausted, and cleanly reported `degraded` status with exact error diagnostics rather than crashing the pipeline.

---

## 4. Credential Protection & Configuration

### Safe `.env` Management
- Credentials must be stored exclusively in `.env` (which is excluded from Git via `.gitignore`).
- Committed `.env.example` contains sanitized placeholders only.
- Keys are never output in terminal logs, stack traces, API serialization payloads, or frontend state.

```ini
# Groq API Configuration
GROQ_KEY=gsk_...
GROQ_KEY2=gsk_...
GROQ_KEY3=gsk_...
GROQ_MODEL=openai/gpt-oss-120b
GROQ_BASE_URL=https://api.groq.com/openai/v1

# Gemini API Configuration
GEMINI_KEY=AQ.Ab8RN6...
GEMINI_KEY2=AQ.Ab8RN6...
GEMINI_KEY3=AQ.Ab8RN6...
GEMINI_MODEL=gemini-2.5-flash
```

### Checking Provider Health via API
Diagnostics can be queried at runtime:
```bash
curl -s http://localhost:8000/api/v1/settings/llm/status
```
Returns slot health, circuit breaker state (`closed` / `open`), and configured models.

