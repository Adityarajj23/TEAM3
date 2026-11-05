# Repository Ingestion & Architecture Mapping — TraceTest AI

## 1. Overview

The Repository Ingestion Engine transforms arbitrary software source repositories into structured, verifiable TraceTest AI projects. It performs shallow cloning, directory traversal, language classification, Python AST parsing, route discovery, and automated requirement generation.

---

## 2. Ingestion Pipeline Workflow

```
[ Git Clone / Local Path ]
          |
          v
[ Directory Tree Scanner ]  ---> Filters: .git, node_modules, dist, __pycache__
          |
          v
[ AST & Source Parsers ]
  - Python AST: Lambda handlers, RPC action dispatches, query keys
  - Frontend Scanners: React routes, API client base URLs, form schemas
          |
          v
[ Architecture Synthesis ]
  - Framework detection (React 18, Vite, Tailwind, AWS Lambda, DynamoDB)
  - Module decomposition (8 functional modules)
  - Endpoint discovery (POST https://bnbpmiljw9.execute-api.ap-south-1.amazonaws.com)
          |
          v
[ Requirements & Test Synthesis ]
  - Provenance tagging (5 levels)
  - Clause extraction & AC formulation
  - Pytest / Contract test generation
          |
          v
[ Database Persistence ] ---> Project, Modules, Environments, Reqs, ACs, Tests
```

---

## 3. Ingesting EchoBox (`sohan10012/EchoBox`)

EchoBox was ingested via the TraceTest AI repository import service:
- **Repository URL**: `https://github.com/sohan10012/EchoBox.git`
- **Default Branch**: `main`
- **Owner**: `sohan10012`
- **Local Storage Path**: `var/repos/EchoBox`

### 3.1 Codebase Inventory

| Language / Asset Type | File Count | Primary Components |
| :--- | :--- | :--- |
| **TypeScript / TSX** | 22 | React UI (`RoomView`, `JoinRoom`, `CreateRoomModal`, `DiscoveryView`, `Toast`) |
| **Python** | 1 | `backend/lambda_function.py` (790 lines, 13 RPC actions) |
| **JSON** | 3 | `package.json`, `tsconfig.json` |
| **CSS** | 1 | `src/index.css` (Tailwind directives) |
| **Markdown** | 2 | `README.md`, `docs/BACKEND_SECURITY_AUDIT.md` |

### 3.2 AST Parsing on AWS Lambda Backend

Parsing `backend/lambda_function.py` revealed the central RPC action dispatcher:
```python
action = body.get("action")
if action == "get_room": ...
elif action in ("discover_rooms", "search_rooms"): ...
elif action == "submit_feedback": ...
elif action == "create_room": ...
# Authenticated actions
elif action == "get_my_posts": ...
elif action == "delete_my_post": ...
elif action == "get_owner_rooms": ...
elif action == "delete_feedback": ...
elif action == "close_room": ...
elif action == "reopen_room": ...
elif action == "claim_legacy_room": ...
```

### 3.3 Extracted Modules for Project `ECHO`

1. `ECHO-ROOMS`: Room Lifecycle (creation, metadata, status transitions)
2. `ECHO-DISCOVERY`: Public Discovery (search, active filter, count aggregation)
3. `ECHO-CHAT`: Anonymous Conversation (session pseudonymity, messages, display names)
4. `ECHO-OWNER`: Room Ownership (owner sub verification, closure, moderation)
5. `ECHO-IDENTITY`: EchoBox Identity (registered author posts, author-only deletion)
6. `ECHO-EXPIRY`: Ephemeral Lifecycle (24-hour limit, HTTP 410 Gone, TTL)
7. `ECHO-SECURITY`: Security & Abuse Protection (64KB payload cap, CORS headers)
8. `ECHO-FRONTEND`: User Experience (Vite React UI, join validation, toast notifications)

---

## 4. API Usage: Ingesting Repositories

### Endpoint: `POST /api/v1/projects/import-repo`

**Request Body**:
```json
{
  "repo_url": "https://github.com/sohan10012/EchoBox.git",
  "branch": "main",
  "project_key": "ECHO",
  "project_name": "EchoBox — Anonymous Conversation Platform",
  "dry_run": false
}
```

**Response (HTTP 201 Created)**:
```json
{
  "ok": true,
  "project": {
    "id": 5,
    "key": "ECHO",
    "name": "EchoBox — Anonymous Conversation Platform",
    "status": "active",
    "stats": {
      "requirements": 21,
      "tests": 21,
      "suites": 0,
      "open_defects": 5,
      "coverage_pct": 100.0
    }
  },
  "analysis": {
    "repo_name": "EchoBox",
    "branch": "main",
    "commit_sha": "d32789f...",
    "file_count": 29,
    "languages": {
      "Python": 1,
      "TypeScript (React)": 18,
      "TypeScript": 4,
      "JSON": 3,
      "Markdown": 2
    },
    "actions_found": [
      "claim_legacy_room", "close_room", "create_room", "delete_feedback",
      "delete_my_post", "discover_rooms", "get_feedback", "get_my_posts",
      "get_owner_rooms", "get_room", "reopen_room", "search_rooms", "submit_feedback"
    ]
  }
}
```
