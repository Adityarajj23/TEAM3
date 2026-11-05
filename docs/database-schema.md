# Database schema

TraceTest AI stores all business and application data in a single SQLite database
(`$TRACETEST_DATA_DIR/tracetest.db`, WAL mode, `foreign_keys=ON`, `busy_timeout=10000`). LangGraph workflow
checkpoints live in a second SQLite file (`workflow_checkpoints.db`) managed by `langgraph-checkpoint-sqlite`.
Files (logs, junit XML, screenshots, uploads, backups) live under the data directory; their paths, sizes and
SHA-256 hashes are stored in SQLite (`execution_artifacts`, audit details).

The schema is created and evolved only through Alembic (`backend/migrations`). This file is generated from the
SQLAlchemy models.

## `ai_cache`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `prompt_hash` | VARCHAR(64) | no |  |
| `task` | VARCHAR(60) | no |  |
| `provider` | VARCHAR(30) | no |  |
| `model` | VARCHAR(100) | no |  |
| `response` | JSON | no |  |
| `created_at` | DATETIME | no |  |

Constraints: UNIQUE(prompt_hash, task)

## `login_attempts`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `email` | VARCHAR(255) | no | indexed |
| `ip` | VARCHAR(64) | yes |  |
| `success` | BOOLEAN | no |  |
| `created_at` | DATETIME | no |  |

## `organisations`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `name` | VARCHAR(200) | no | unique |
| `slug` | VARCHAR(80) | no | unique |
| `created_at` | DATETIME | no |  |

Constraints: UNIQUE(slug); UNIQUE(name)

## `roles`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `name` | VARCHAR(50) | no | unique |
| `description` | VARCHAR(255) | no |  |

Constraints: UNIQUE(name)

## `users`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `email` | VARCHAR(255) | no | unique, indexed |
| `full_name` | VARCHAR(200) | no |  |
| `title` | VARCHAR(120) | yes |  |
| `password_hash` | VARCHAR(255) | yes |  |
| `is_active` | BOOLEAN | no |  |
| `can_login` | BOOLEAN | no |  |
| `created_at` | DATETIME | no |  |
| `last_login_at` | DATETIME | yes |  |

## `eval_runs`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `provider` | VARCHAR(30) | no |  |
| `model` | VARCHAR(100) | no |  |
| `is_fixture` | BOOLEAN | no |  |
| `status` | VARCHAR(20) | no |  |
| `metrics` | JSON | no |  |
| `scenario_count` | INTEGER | no |  |
| `error` | TEXT | yes |  |
| `triggered_by` | INTEGER | yes | FK → `users.id` |
| `started_at` | DATETIME | no |  |
| `finished_at` | DATETIME | yes |  |

## `notifications`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `user_id` | INTEGER | no | FK → `users.id` ON DELETE CASCADE, indexed |
| `title` | VARCHAR(200) | no |  |
| `body` | TEXT | no |  |
| `link` | VARCHAR(300) | yes |  |
| `read` | BOOLEAN | no |  |
| `created_at` | DATETIME | no |  |

## `projects`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `key` | VARCHAR(10) | no | unique |
| `name` | VARCHAR(200) | no |  |
| `description` | TEXT | no |  |
| `status` | VARCHAR(20) | no |  |
| `organisation_id` | INTEGER | no | FK → `organisations.id` |
| `owner_id` | INTEGER | yes | FK → `users.id` |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

Constraints: UNIQUE(key); CHECK `status in ('active','archived')`

## `reviews`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `entity_type` | VARCHAR(30) | no |  |
| `entity_id` | INTEGER | no | indexed |
| `entity_version` | INTEGER | no |  |
| `decision` | VARCHAR(30) | no |  |
| `comment` | TEXT | no |  |
| `reviewer_id` | INTEGER | no | FK → `users.id` |
| `created_at` | DATETIME | no |  |

Constraints: INDEX ix_reviews_entity(entity_type, entity_id)

## `runs`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `kind` | VARCHAR(40) | no | indexed |
| `status` | VARCHAR(20) | no | indexed |
| `subject_type` | VARCHAR(30) | yes |  |
| `subject_id` | INTEGER | yes |  |
| `thread_id` | VARCHAR(80) | yes |  |
| `progress` | FLOAT | no |  |
| `message` | VARCHAR(500) | no |  |
| `result` | JSON | no |  |
| `error` | TEXT | yes |  |
| `created_by` | INTEGER | yes | FK → `users.id` |
| `created_at` | DATETIME | no |  |
| `started_at` | DATETIME | yes |  |
| `finished_at` | DATETIME | yes |  |

## `sessions`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `token_hash` | VARCHAR(64) | no | unique, indexed |
| `csrf_token` | VARCHAR(64) | no |  |
| `user_id` | INTEGER | no | FK → `users.id` ON DELETE CASCADE, indexed |
| `created_at` | DATETIME | no |  |
| `expires_at` | DATETIME | no |  |
| `revoked` | BOOLEAN | no |  |
| `ip` | VARCHAR(64) | yes |  |

## `user_roles`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `user_id` | INTEGER | no | FK → `users.id` ON DELETE CASCADE |
| `role_id` | INTEGER | no | FK → `roles.id` ON DELETE CASCADE |

Constraints: UNIQUE(user_id, role_id)

## `audit_log`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `actor_id` | INTEGER | yes | FK → `users.id`, indexed |
| `action` | VARCHAR(80) | no | indexed |
| `entity_type` | VARCHAR(40) | no | indexed |
| `entity_id` | INTEGER | yes |  |
| `entity_key` | VARCHAR(60) | yes |  |
| `project_id` | INTEGER | yes | FK → `projects.id` ON DELETE SET NULL, indexed |
| `source` | VARCHAR(30) | no |  |
| `details` | JSON | no |  |
| `trace_id` | VARCHAR(40) | yes |  |
| `created_at` | DATETIME | no | indexed |

## `environments`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `project_id` | INTEGER | no | FK → `projects.id` ON DELETE CASCADE, indexed |
| `name` | VARCHAR(80) | no |  |
| `kind` | VARCHAR(20) | no |  |
| `hcm_version` | VARCHAR(10) | yes |  |
| `base_url` | VARCHAR(500) | yes |  |
| `is_default` | BOOLEAN | no |  |
| `created_at` | DATETIME | no |  |

Constraints: UNIQUE(project_id, name)

## `eval_results`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `eval_run_id` | INTEGER | no | FK → `eval_runs.id` ON DELETE CASCADE, indexed |
| `scenario_key` | VARCHAR(60) | no |  |
| `passed` | BOOLEAN | no |  |
| `metrics` | JSON | no |  |
| `notes` | TEXT | no |  |

## `integrations`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `project_id` | INTEGER | no | FK → `projects.id` ON DELETE CASCADE |
| `kind` | VARCHAR(30) | no |  |
| `config` | JSON | no |  |
| `status` | VARCHAR(20) | no |  |
| `last_checked_at` | DATETIME | yes |  |
| `created_at` | DATETIME | no |  |

Constraints: UNIQUE(project_id, kind)

## `modules`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `project_id` | INTEGER | no | FK → `projects.id` ON DELETE CASCADE, indexed |
| `code` | VARCHAR(20) | no |  |
| `name` | VARCHAR(200) | no |  |
| `description` | TEXT | no |  |

Constraints: UNIQUE(project_id, code)

## `project_members`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `project_id` | INTEGER | no | FK → `projects.id` ON DELETE CASCADE, indexed |
| `user_id` | INTEGER | no | FK → `users.id` ON DELETE CASCADE, indexed |
| `project_role` | VARCHAR(40) | no |  |
| `added_at` | DATETIME | no |  |

Constraints: UNIQUE(project_id, user_id)

## `provider_traces`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `run_id` | INTEGER | yes | FK → `runs.id` ON DELETE SET NULL, indexed |
| `provider` | VARCHAR(30) | no |  |
| `model` | VARCHAR(100) | no |  |
| `task` | VARCHAR(60) | no |  |
| `prompt_hash` | VARCHAR(64) | no | indexed |
| `status` | VARCHAR(20) | no |  |
| `latency_ms` | INTEGER | no |  |
| `attempt` | INTEGER | no |  |
| `input_tokens` | INTEGER | yes |  |
| `output_tokens` | INTEGER | yes |  |
| `error` | TEXT | yes |  |
| `response_text` | TEXT | yes |  |
| `created_at` | DATETIME | no |  |

## `run_steps`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `run_id` | INTEGER | no | FK → `runs.id` ON DELETE CASCADE, indexed |
| `name` | VARCHAR(80) | no |  |
| `status` | VARCHAR(20) | no |  |
| `detail` | JSON | no |  |
| `started_at` | DATETIME | no |  |
| `finished_at` | DATETIME | yes |  |

## `integration_events`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `integration_id` | INTEGER | yes | FK → `integrations.id` ON DELETE CASCADE, indexed |
| `kind` | VARCHAR(40) | no |  |
| `status` | VARCHAR(20) | no |  |
| `request_summary` | TEXT | no |  |
| `response_summary` | TEXT | no |  |
| `created_at` | DATETIME | no |  |

## `requirements`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `key` | VARCHAR(40) | no | unique, indexed |
| `project_id` | INTEGER | no | FK → `projects.id` ON DELETE CASCADE, indexed |
| `module_id` | INTEGER | yes | FK → `modules.id` ON DELETE SET NULL |
| `title` | VARCHAR(300) | no |  |
| `category` | VARCHAR(40) | no |  |
| `priority` | VARCHAR(10) | no |  |
| `status` | VARCHAR(20) | no | indexed |
| `current_version` | INTEGER | no |  |
| `author_id` | INTEGER | yes | FK → `users.id` |
| `source_type` | VARCHAR(20) | no |  |
| `analysed_at` | DATETIME | yes |  |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

## `test_suites`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `key` | VARCHAR(40) | no | unique |
| `project_id` | INTEGER | no | FK → `projects.id` ON DELETE CASCADE, indexed |
| `module_id` | INTEGER | yes | FK → `modules.id` ON DELETE SET NULL |
| `name` | VARCHAR(200) | no |  |
| `description` | TEXT | no |  |
| `priority` | VARCHAR(10) | no |  |
| `created_by` | INTEGER | yes | FK → `users.id` |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

Constraints: UNIQUE(key); UNIQUE(project_id, name)

## `acceptance_criteria`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `key` | VARCHAR(60) | no | unique |
| `requirement_id` | INTEGER | no | FK → `requirements.id` ON DELETE CASCADE, indexed |
| `requirement_version` | INTEGER | no |  |
| `clause_keys` | JSON | no |  |
| `description` | TEXT | no |  |
| `preconditions` | TEXT | no |  |
| `expected_behaviour` | TEXT | no |  |
| `validation_conditions` | JSON | no |  |
| `source_quote` | TEXT | no |  |
| `quote_verified` | BOOLEAN | no |  |
| `confidence` | FLOAT | no |  |
| `rationale` | TEXT | no |  |
| `assumptions` | JSON | no |  |
| `review_status` | VARCHAR(20) | no |  |
| `provider` | VARCHAR(40) | no |  |
| `model` | VARCHAR(100) | yes |  |
| `created_at` | DATETIME | no |  |

Constraints: UNIQUE(key)

## `executions`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `key` | VARCHAR(40) | no | unique |
| `project_id` | INTEGER | no | FK → `projects.id` ON DELETE CASCADE, indexed |
| `suite_id` | INTEGER | yes | FK → `test_suites.id` ON DELETE SET NULL, indexed |
| `environment_id` | INTEGER | no | FK → `environments.id` |
| `run_id` | INTEGER | yes | FK → `runs.id` ON DELETE SET NULL |
| `retry_of_id` | INTEGER | yes | FK → `executions.id` ON DELETE SET NULL |
| `source` | VARCHAR(30) | no | indexed |
| `runner` | VARCHAR(20) | no |  |
| `status` | VARCHAR(20) | no | indexed |
| `hcm_version` | VARCHAR(10) | yes |  |
| `total` | INTEGER | no |  |
| `passed` | INTEGER | no |  |
| `failed` | INTEGER | no |  |
| `errored` | INTEGER | no |  |
| `skipped` | INTEGER | no |  |
| `duration_ms` | INTEGER | no |  |
| `commit_sha` | VARCHAR(64) | yes |  |
| `branch` | VARCHAR(200) | yes |  |
| `triggered_by` | INTEGER | yes | FK → `users.id` |
| `log_excerpt` | TEXT | no |  |
| `started_at` | DATETIME | yes | indexed |
| `finished_at` | DATETIME | yes |  |
| `created_at` | DATETIME | no |  |

Constraints: UNIQUE(key); CHECK `status in ('queued','running','passed','failed','error','cancelled','timed_out')`

## `requirement_versions`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `requirement_id` | INTEGER | no | FK → `requirements.id` ON DELETE CASCADE, indexed |
| `version` | INTEGER | no |  |
| `title` | VARCHAR(300) | no |  |
| `description` | TEXT | no |  |
| `business_objective` | TEXT | no |  |
| `content_hash` | VARCHAR(64) | no |  |
| `change_summary` | VARCHAR(500) | no |  |
| `author_id` | INTEGER | yes | FK → `users.id` |
| `created_at` | DATETIME | no |  |

Constraints: UNIQUE(requirement_id, version)

## `test_cases`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `key` | VARCHAR(40) | no | unique, indexed |
| `project_id` | INTEGER | no | FK → `projects.id` ON DELETE CASCADE, indexed |
| `requirement_id` | INTEGER | no | FK → `requirements.id` ON DELETE CASCADE, indexed |
| `requirement_version` | INTEGER | no |  |
| `clause_keys` | JSON | no |  |
| `ac_keys` | JSON | no |  |
| `title` | VARCHAR(300) | no |  |
| `description` | TEXT | no |  |
| `preconditions` | TEXT | no |  |
| `test_data` | JSON | no |  |
| `expected_result` | TEXT | no |  |
| `priority` | VARCHAR(10) | no |  |
| `test_type` | VARCHAR(20) | no | indexed |
| `confidence` | FLOAT | no |  |
| `source_quote` | TEXT | no |  |
| `quote_verified` | BOOLEAN | no |  |
| `rationale` | TEXT | no |  |
| `automation` | VARCHAR(20) | no |  |
| `script` | TEXT | yes |  |
| `script_hash` | VARCHAR(64) | yes |  |
| `validation_status` | VARCHAR(20) | no |  |
| `validation_errors` | JSON | no |  |
| `version` | INTEGER | no |  |
| `status` | VARCHAR(30) | no | indexed |
| `needs_reapproval_reason` | VARCHAR(500) | yes |  |
| `reviewer_id` | INTEGER | yes | FK → `users.id` |
| `provider` | VARCHAR(40) | no |  |
| `model` | VARCHAR(100) | yes |  |
| `duplicate_of` | VARCHAR(40) | yes |  |
| `created_by` | INTEGER | yes | FK → `users.id` |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

## `clauses`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `version_id` | INTEGER | no | FK → `requirement_versions.id` ON DELETE CASCADE, indexed |
| `requirement_id` | INTEGER | no | FK → `requirements.id` ON DELETE CASCADE, indexed |
| `clause_key` | VARCHAR(60) | no | indexed |
| `position` | INTEGER | no |  |
| `text` | TEXT | no |  |
| `normalized_hash` | VARCHAR(64) | no |  |
| `ambiguity_flags` | JSON | no |  |
| `analysis` | JSON | no |  |

Constraints: UNIQUE(version_id, clause_key)

## `execution_results`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `execution_id` | INTEGER | no | FK → `executions.id` ON DELETE CASCADE, indexed |
| `test_case_id` | INTEGER | no | FK → `test_cases.id` ON DELETE CASCADE, indexed |
| `test_case_version` | INTEGER | no |  |
| `script_hash` | VARCHAR(64) | yes |  |
| `status` | VARCHAR(20) | no | indexed |
| `duration_ms` | INTEGER | no |  |
| `message` | TEXT | no |  |
| `stack_trace` | TEXT | no |  |
| `stdout` | TEXT | no |  |
| `failure_analysis` | JSON | yes |  |
| `started_at` | DATETIME | yes |  |
| `finished_at` | DATETIME | yes |  |

Constraints: UNIQUE(execution_id, test_case_id); CHECK `status in ('passed','failed','skipped','error','cancelled','timed_out')`

## `suite_test_cases`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `suite_id` | INTEGER | no | FK → `test_suites.id` ON DELETE CASCADE, indexed |
| `test_case_id` | INTEGER | no | FK → `test_cases.id` ON DELETE CASCADE, indexed |
| `position` | INTEGER | no |  |

Constraints: UNIQUE(suite_id, test_case_id)

## `test_case_versions`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `test_case_id` | INTEGER | no | FK → `test_cases.id` ON DELETE CASCADE, indexed |
| `version` | INTEGER | no |  |
| `snapshot` | JSON | no |  |
| `script_hash` | VARCHAR(64) | yes |  |
| `changed_by` | INTEGER | yes | FK → `users.id` |
| `change_note` | VARCHAR(500) | no |  |
| `created_at` | DATETIME | no |  |

Constraints: UNIQUE(test_case_id, version)

## `test_steps`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `test_case_id` | INTEGER | no | FK → `test_cases.id` ON DELETE CASCADE, indexed |
| `position` | INTEGER | no |  |
| `action` | TEXT | no |  |
| `expected` | TEXT | no |  |

Constraints: UNIQUE(test_case_id, position)

## `defects`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `key` | VARCHAR(40) | no | unique, indexed |
| `project_id` | INTEGER | no | FK → `projects.id` ON DELETE CASCADE, indexed |
| `title` | VARCHAR(300) | no |  |
| `description` | TEXT | no |  |
| `severity` | VARCHAR(10) | no | indexed |
| `priority` | VARCHAR(10) | no |  |
| `status` | VARCHAR(20) | no | indexed |
| `approval_status` | VARCHAR(20) | no |  |
| `requirement_id` | INTEGER | yes | FK → `requirements.id` ON DELETE SET NULL |
| `test_case_id` | INTEGER | yes | FK → `test_cases.id` ON DELETE SET NULL |
| `execution_id` | INTEGER | yes | FK → `executions.id` ON DELETE SET NULL |
| `execution_result_id` | INTEGER | yes | FK → `execution_results.id` ON DELETE SET NULL |
| `expected_result` | TEXT | no |  |
| `actual_result` | TEXT | no |  |
| `reproduction_steps` | TEXT | no |  |
| `error_log` | TEXT | no |  |
| `stack_trace` | TEXT | no |  |
| `ai_analysis` | JSON | yes |  |
| `owner_id` | INTEGER | yes | FK → `users.id` |
| `reporter_id` | INTEGER | yes | FK → `users.id` |
| `verified_execution_id` | INTEGER | yes | FK → `executions.id` ON DELETE SET NULL |
| `github_issue_url` | VARCHAR(500) | yes |  |
| `github_issue_number` | INTEGER | yes |  |
| `github_issue_state` | VARCHAR(20) | yes |  |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |
| `resolved_at` | DATETIME | yes |  |

Constraints: CHECK `status in ('open','triaged','assigned','in_progress','fixed','ready_for_retest','verified','closed','reopened')`

## `execution_artifacts`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `execution_id` | INTEGER | no | FK → `executions.id` ON DELETE CASCADE, indexed |
| `result_id` | INTEGER | yes | FK → `execution_results.id` ON DELETE CASCADE |
| `kind` | VARCHAR(30) | no |  |
| `path` | VARCHAR(500) | no |  |
| `size_bytes` | INTEGER | no |  |
| `sha256` | VARCHAR(64) | no |  |
| `created_at` | DATETIME | no |  |

## `defect_comments`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `defect_id` | INTEGER | no | FK → `defects.id` ON DELETE CASCADE, indexed |
| `author_id` | INTEGER | no | FK → `users.id` |
| `body` | TEXT | no |  |
| `created_at` | DATETIME | no |  |

## `defect_links`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `defect_id` | INTEGER | no | FK → `defects.id` ON DELETE CASCADE, indexed |
| `related_defect_id` | INTEGER | no | FK → `defects.id` ON DELETE CASCADE |
| `link_type` | VARCHAR(20) | no |  |

Constraints: UNIQUE(defect_id, related_defect_id)
