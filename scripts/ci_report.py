"""Post a junit XML report to TraceTest (`POST /api/v1/ci/results`). Requires TRACETEST_URL and TRACETEST_CI_TOKEN."""
import json
import os
import sys
import urllib.request

url, token = os.environ.get("TRACETEST_URL"), os.environ.get("TRACETEST_CI_TOKEN")
if not url or not token:
    print("TRACETEST_URL / TRACETEST_CI_TOKEN not set; skipping upload")
    raise SystemExit(0)
junit, project, version = sys.argv[1], sys.argv[2], sys.argv[3]
body = json.dumps({"project_key": project, "environment": version, "commit_sha": os.environ.get("GITHUB_SHA", "local"),
                   "branch": os.environ.get("GITHUB_REF_NAME", "local"), "junit_xml": open(junit).read()}).encode()
req = urllib.request.Request(url.rstrip("/") + "/api/v1/ci/results", data=body, method="POST",
                             headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
with urllib.request.urlopen(req, timeout=30) as r:
    print(r.status, r.read().decode())
