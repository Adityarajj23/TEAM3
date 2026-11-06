// Response shapes returned by the API (request bodies use the OpenAPI-generated Schemas types).
export interface Page<T> { items: T[]; total: number; page: number; page_size: number }
export interface UserRef { id: number; name: string; email: string }
export interface User { id: number; email: string; full_name: string; title: string | null; is_active: boolean;
  can_login: boolean; roles: string[]; last_login_at: string | null; created_at: string }
export interface Me { user: User; roles: string[]; permissions: string[]; csrf_token: string; project_ids: number[] }
export interface Module { id: number; project_id: number; code: string; name: string; description: string }
export interface Environment { id: number; project_id: number; name: string; kind: string; hcm_version: string | null;
  base_url: string | null; is_default: boolean }
export interface Project { id: number; key: string; name: string; description: string; status: string;
  stats: { requirements: number; tests: number; suites: number; open_defects: number; members: number; coverage_pct: number };
  modules?: Module[]; environments?: Environment[]; members?: { user: User; project_role: string }[] }
export interface Clause { id: number; clause_key: string; position: number; text: string;
  ambiguity_flags: { term: string; reason: string }[]; analysis: Record<string, any> }
export interface RequirementVersion { id: number; version: number; title: string; description: string;
  business_objective: string; change_summary: string; author: UserRef | null; created_at: string; clauses?: Clause[] }
export interface Requirement { id: number; key: string; project_id: number; project_key: string; module: Module | null;
  title: string; category: string; priority: string; status: string; version: number; source_type: string;
  author: UserRef | null; analysed_at: string | null; created_at: string; updated_at: string;
  current?: RequirementVersion; clauses?: Clause[]; test_count?: number }
export interface Criterion { id: number; key: string; clause_keys: string[]; description: string; preconditions: string;
  expected_behaviour: string; validation_conditions: string[]; source_quote: string; quote_verified: boolean;
  confidence: number; rationale: string; assumptions: string[]; review_status: string; provider: string; model: string | null }
export interface TestCase { id: number; key: string; project_id: number; requirement_id: number; requirement_key: string;
  requirement_version: number; clause_keys: string[]; ac_keys: string[]; title: string; priority: string; test_type: string;
  confidence: number; automation: string; status: string; validation_status: string; version: number; provider: string;
  model: string | null; duplicate_of: string | null; quote_verified: boolean; needs_reapproval_reason: string | null;
  updated_at: string; description?: string; preconditions?: string; test_data?: Record<string, any>;
  expected_result?: string; source_quote?: string; rationale?: string; script?: string | null; script_hash?: string | null;
  validation_errors?: string[]; steps?: { position: number; action: string; expected: string }[];
  created_by?: UserRef | null; reviewer?: UserRef | null; reviews?: any[]; versions?: any[]; recent_results?: ExecResult[];
  executable?: boolean; blocked_reason?: string }
export interface Suite { id: number; key: string; project_id: number; module: Module | null; name: string; description: string;
  priority: string; test_count: number | null; tests?: TestCase[]; executions?: Execution[];
  coverage?: { requirements: number; clauses: number; covered: number } }
export interface Execution { id: number; key: string; project_id: number; suite: { id: number; key: string; name: string } | null;
  environment: Environment | null; source: string; runner: string; status: string; isolation_level?: string; hcm_version: string | null; total: number;
  passed: number; failed: number; errored: number; skipped: number; duration_ms: number; commit_sha: string | null;
  branch: string | null; retry_of_id: number | null; run_id: number | null; triggered_by: UserRef | null;
  started_at: string | null; finished_at: string | null; results?: ExecResult[];
  artifacts?: { id: number; kind: string; name: string; size_bytes: number; sha256: string }[] }
export interface ExecResult { id: number; execution_id: number; test_case_id: number; test_key: string; test_title: string;
  test_case_version: number; script_hash: string | null; status: string; duration_ms: number; message: string;
  stack_trace: string; stdout: string; failure_analysis: Record<string, any> | null }
export interface Defect { id: number; key: string; project_id: number; title: string; severity: string; priority: string;
  status: string; approval_status: string; evidence_type?: string; source_commit_sha?: string | null; owner: UserRef | null; test_case_id: number | null; requirement_id: number | null;
  execution_id: number | null; github_issue_url: string | null; github_issue_state: string | null; created_at: string;
  updated_at: string; resolved_at: string | null; description?: string; expected_result?: string; actual_result?: string;
  reproduction_steps?: string; error_log?: string; stack_trace?: string; ai_analysis?: Record<string, any> | null;
  reporter?: UserRef | null; execution_result_id?: number | null; test_key?: string | null; requirement_key?: string | null;
  execution_key?: string | null; github_issue_number?: number | null; verified_execution?: { id: number; key: string } | null;
  comments?: { id: number; author: UserRef; body: string; at: string }[];
  links?: { type: string; key: string; id: number; title: string; status: string }[];
  duplicate_candidates?: { key: string; id: number; title: string; status: string; score: number }[];
  allowed_transitions?: string[] }
export interface Run { id: number; kind: string; status: string; progress: number; message: string; result: Record<string, any>;
  error: string | null; steps?: { name: string; status: string; detail: any; at: string }[] }
export interface AuditEntry { id: number; actor: UserRef | null; action: string; entity_type: string; entity_id: number | null;
  entity_key: string | null; project_id: number | null; source: string; details: Record<string, any>; trace_id: string | null;
  created_at: string }
