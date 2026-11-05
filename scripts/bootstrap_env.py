"""Create .env from .env.example with random development passwords and secret (never overwrites)."""
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
env, example = root / ".env", root / ".env.example"
if env.exists():
    print(".env already exists; leaving it unchanged")
    raise SystemExit(0)
lines = []
for line in example.read_text().splitlines():
    if line.startswith(("TRACETEST_ADMIN_PASSWORD=", "TRACETEST_QA_PASSWORD=", "TRACETEST_REVIEWER_PASSWORD=")):
        line = line.split("=")[0] + "=" + secrets.token_urlsafe(12)
    elif line.startswith("TRACETEST_SECRET_KEY="):
        line = "TRACETEST_SECRET_KEY=" + secrets.token_urlsafe(48)
    lines.append(line)
env.write_text("\n".join(lines) + "\n")
print("Wrote .env with generated development passwords. Read them from .env to sign in.")
