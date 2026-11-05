# Security

| Control | Implementation |
|---|---|
| Passwords | Argon2id (`argon2-cffi`). Dev account passwords only from environment variables; accounts without one cannot sign in. |
| Sessions | 256-bit random token in an HttpOnly, SameSite=Lax cookie (`Secure` via `TRACETEST_COOKIE_SECURE`); only an HMAC-SHA256 of the token is stored; expiry and revocation on logout. |
| CSRF | Per-session token returned at login and in a readable cookie; required in `X-CSRF-Token` on every non-GET request and compared in constant time. |
| Login throttling | 5 failed attempts per account in 15 minutes returns 429; attempts are stored in SQLite. |
| Rate limiting | Sliding one-minute window per session (or client IP), default 600 requests. Per process. |
| Authorisation | Role permissions (`admin`, `qa_engineer`, `reviewer`) checked in every mutating endpoint; authors cannot approve their own tests; defect creation from AI requires a reviewer. |
| Project isolation | Non-admins see only projects they are members of; inaccessible records return 404. |
| Input validation | Pydantic models with length/pattern limits; requirement text sanitised (NFKC, control characters stripped, 20,000 character cap). |
| Uploads | PDF/TXT/MD only, 2 MB cap, PDF magic-byte check, UTF-8 enforced, stored under a content hash. |
| Prompt injection | Requirement text is wrapped as untrusted data, scanned for injection markers (recorded in audit and run results) and never able to change system behaviour; all outputs are re-validated deterministically. |
| Secrets | Only from the environment; `/config` returns configured/not configured status, never values; keys are never logged or traced. |
| Execution | See `execution-engine.md`. |
| Headers | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin`, `X-Trace-Id`. |
| Audit | Every state change is recorded with actor, record, project, source and trace ID. |

## Known limitations

- The sandbox is not a container or VM; a determined attacker who bypasses the AST allowlist could still affect the
  host within the process limits. Deploy on a dedicated host or add a container runtime for untrusted authors.
- Rate limiting and the background worker pool are per process.
- No SSO or MFA; local accounts only.
- The development server does not terminate TLS; put the API behind a TLS proxy and set `TRACETEST_COOKIE_SECURE=true`.
- Google Fonts are loaded from Google's CDN by the frontend.
