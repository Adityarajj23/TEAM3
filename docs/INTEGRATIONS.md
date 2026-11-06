# External Integrations Guide — TraceTest AI

## 1. Overview

TraceTest AI integrates with version control platforms (GitHub), cloud infrastructure (AWS API Gateway / Lambda), and CI/CD automation pipelines to support continuous verification across the software development lifecycle.

---

## 2. GitHub Integration

The GitHub integration enables automatic repository cloning, defect synchronisation, and pull request commit tracking.

### 2.1 Configuration
Stored per-project under the `Integration` table:
```json
{
  "project_id": 5,
  "kind": "github",
  "config": {
    "repo": "sohan10012/EchoBox",
    "branch": "main",
    "delivery_repo": "sohan10012/TEAM3"
  },
  "status": "connected"
}
```

### 2.2 GitHub Issues Sync
When a defect is triaged or approved in TraceTest AI, it can be exported as a GitHub issue:
- `POST /api/v1/defects/{id}/export-github`
- Formats markdown issue description with reproduction steps, affected requirement clauses, error log excerpt, and AI root-cause analysis.
- Stores `github_issue_url` and `github_issue_number` on the `Defect` record.

---

## 3. AWS Serverless & Cloud Integrations

Demonstrated in the EchoBox case study:
- **AWS API Gateway HTTP API**: Targeted via REST dispatcher in `src/api/client.ts`.
- **AWS Lambda**: Multi-action Python RPC backend.
- **Amazon DynamoDB**: Single-table key-value storage.
- **Amazon Cognito**: Dual user pool JWT token verification.

### Probe Diagnostics
The platform includes an HTTP probe runner capable of evaluating cloud endpoints:
```python
import urllib.request, json
req = urllib.request.Request(
    "https://<api-id>.execute-api.ap-south-1.amazonaws.com",
    data=json.dumps({"action": "discover_rooms"}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST"
)
```

---

## 4. CI/CD Webhook & Pipeline Integration

### Triggering Executions from CI
Automated pipelines (GitHub Actions, GitLab CI, Jenkins) can trigger test executions via REST:

```bash
curl -X POST http://localhost:8000/api/v1/projects/5/executions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{
    "environment_id": 1,
    "source": "ci",
    "commit_sha": "${{ github.sha }}",
    "branch": "${{ github.ref_name }}"
  }'
```

The endpoint returns an execution key (e.g. `EX-000002`). Pipelines can poll `GET /api/v1/executions/EX-000002` until `status` resolves to `passed` or `failed`.

