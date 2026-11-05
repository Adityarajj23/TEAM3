import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Fragment, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { DataTable, FilterChips } from "@/components/DataTable";
import { RunProgress } from "@/components/RunProgress";
import { useToast } from "@/components/Toast";
import { Badge, Button, Code, EmptyState, ErrorState, Field, Input, Key, KV, LoadingBlock, Notice, PageHeader, Panel, Select, Stat } from "@/components/ui";
import { useAuth } from "@/hooks/useAuth";
import { useListState } from "@/hooks/useListState";
import { useProjects } from "@/hooks/useProjects";
import { api, downloadUrl } from "@/services/api";
import type { AuditEntry, Page, Requirement, User } from "@/types/models";
import { cn, fmtDate, label, pct } from "@/utils/format";

// ---------------- traceability ----------------
const CELL: Record<string, { cls: string; text: string }> = {
  passed: { cls: "bg-emerald-600", text: "Approved, last run passed" },
  approved: { cls: "bg-emerald-300", text: "Approved, not yet run" },
  failed_execution: { cls: "bg-red-600", text: "Approved, last run failed" },
  pending_approval: { cls: "bg-amber-300", text: "Pending approval" },
  needs_review: { cls: "bg-violet-400", text: "Needs review or re-approval" },
  rejected: { cls: "bg-slate-300", text: "Rejected" },
};

export function TraceabilityPage() {
  const [sp, setSp] = useSearchParams();
  const { projectId, projects } = useProjects();
  const pid = sp.get("project_id") ?? (projectId ? String(projectId) : String(projects[0]?.id ?? ""));
  const rid = sp.get("requirement_id") ?? "";
  const nav = useNavigate();
  const reqs = useQuery({ queryKey: ["requirements", "trace", pid], enabled: !!pid, queryFn: () => api.get<Page<Requirement>>("/requirements", { project_id: pid, page_size: 200, sort: "key", order: "asc" }) });
  const q = useQuery({ queryKey: ["trace", pid, rid], enabled: !!pid, queryFn: () => api.get<any>("/traceability/matrix", { project_id: pid, requirement_id: rid || undefined }) });
  const [onlyGaps, setOnlyGaps] = useState(false);
  const d = q.data;
  const cellMap = useMemo(() => { const m = new Map<string, string>(); d?.cells.forEach(([c, t, s]: [number, number, string]) => m.set(`${c}:${t}`, s)); return m; }, [d]);
  const rows = (d?.clauses ?? []).filter((c: any) => !onlyGaps || !c.covered);
  const set = (k: string, v: string) => { const n = new URLSearchParams(sp); if (v) n.set(k, v); else n.delete(k); if (k === "project_id") n.delete("requirement_id"); setSp(n, { replace: true }); };
  return (
    <>
      <PageHeader title="Traceability" subtitle="Requirement clauses against the tests that cite them. Select any cell, clause or test to open the record."
        actions={<>
          <Select className="w-60" value={pid} onChange={(e) => set("project_id", e.target.value)} aria-label="Project">{projects.map((p) => <option key={p.id} value={p.id}>{p.key} — {p.name}</option>)}</Select>
          <Select className="w-72" value={rid} onChange={(e) => set("requirement_id", e.target.value)} aria-label="Requirement">
            <option value="">All requirements</option>{reqs.data?.items.map((r) => <option key={r.id} value={r.id}>{r.key} {r.title}</option>)}</Select>
          <a className="text-sm text-accent hover:underline" href={downloadUrl("/exports/traceability.csv", { project_id: pid })}>Export CSV</a></>} />
      {q.error ? <ErrorState error={q.error} onRetry={q.refetch} /> : !d ? <LoadingBlock rows={10} /> : <>
        <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-7">
          <Stat label="Clauses" value={d.summary.total_clauses} />
          <Stat label="Covered" value={d.summary.covered_clauses} />
          <Stat label="Untested" value={d.summary.untested_clauses} intent={d.summary.untested_clauses ? "bad" : "good"} onClick={() => setOnlyGaps(true)} />
          <Stat label="Coverage" value={pct(d.summary.coverage_pct)} />
          <Stat label="Orphan tests" value={d.summary.orphan_tests.length} hint="Cite no current clause" />
          <Stat label="Duplicate tests" value={d.summary.duplicate_tests.length} />
          <Stat label="Impacted tests" value={d.summary.impacted_tests.length} hint="Awaiting re-approval" />
        </div>
        <div className="mb-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-600">
          {Object.entries(CELL).map(([k, v]) => <span key={k} className="flex items-center gap-1.5"><span className={cn("h-3 w-3 rounded-sm", v.cls)} aria-hidden />{v.text}</span>)}
          <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-sm border border-dashed border-red-400" aria-hidden />Not covered</span>
          <label className="ml-auto flex items-center gap-1.5"><input type="checkbox" checked={onlyGaps} onChange={(e) => setOnlyGaps(e.target.checked)} />Show untested clauses only</label>
        </div>
        {!rows.length ? <Panel><EmptyState title={onlyGaps ? "Every clause is covered" : "No clauses in scope"} /></Panel> :
          <div className="overflow-auto rounded-lg border border-slate-200 bg-white" style={{ maxHeight: "calc(100dvh - 22rem)" }}>
            <table className="border-separate border-spacing-0 text-xs" aria-label="Traceability matrix">
              <thead className="sticky top-0 z-20 bg-white">
                <tr>
                  <th scope="col" className="sticky left-0 z-30 min-w-[22rem] border-b border-r border-slate-200 bg-white px-3 py-2 text-left font-medium text-slate-600">Clause</th>
                  {d.tests.map((t: any) => (
                    <th key={t.id} scope="col" className="h-28 w-7 border-b border-slate-200 align-bottom">
                      <Link to={`/tests/${t.id}`} title={`${t.key}: ${t.title}`} className="mx-auto block w-5 pb-1 font-mono text-[10px] font-normal text-slate-500 hover:text-accent [writing-mode:vertical-rl] rotate-180">{t.key.replace(/^TC-/, "")}</Link>
                    </th>))}
                </tr>
              </thead>
              <tbody>
                {rows.map((c: any, i: number) => {
                  const newReq = i === 0 || rows[i - 1].requirement_key !== c.requirement_key;
                  return (
                    <Fragment key={c.index}>
                      {newReq && <tr><td colSpan={d.tests.length + 1} className="sticky left-0 border-b border-slate-200 bg-slate-50 px-3 py-1.5">
                        <Link to={`/requirements/${c.requirement_id}`} className="font-mono text-2xs font-medium text-slate-700 hover:text-accent">{c.requirement_key}</Link></td></tr>}
                      <tr className="group">
                        <th scope="row" className={cn("sticky left-0 z-10 border-b border-r border-slate-100 bg-white px-3 py-1.5 text-left font-normal group-hover:bg-slate-50", !c.covered && "bg-red-50/60")}>
                          <Link to={`/requirements/${c.requirement_id}`} className="flex gap-2"><span className="w-10 shrink-0 font-mono text-slate-500">{c.clause_key.split(".").pop()}</span>
                            <span className="line-clamp-1 text-slate-800" title={c.text}>{c.text}</span>
                            {!c.covered && <span className="shrink-0 text-red-700">untested</span>}</Link>
                        </th>
                        {d.tests.map((t: any, ti: number) => {
                          const s = cellMap.get(`${c.index}:${ti}`);
                          return <td key={t.id} className="border-b border-slate-100 p-0.5 text-center group-hover:bg-slate-50">
                            {s ? <button onClick={() => nav(`/tests/${t.id}`)} title={`${t.key} covers ${c.clause_key}: ${CELL[s]?.text ?? s}`}
                              aria-label={`${t.key} covers ${c.clause_key}, ${CELL[s]?.text ?? s}`}
                              className={cn("mx-auto block h-4 w-4 rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-ring", CELL[s]?.cls ?? "bg-slate-300")} /> : null}
                          </td>;
                        })}
                      </tr>
                    </Fragment>);
                })}
              </tbody>
            </table>
          </div>}
        {(d.summary.orphan_tests.length > 0 || d.summary.duplicate_tests.length > 0) && <div className="mt-4 grid gap-4 md:grid-cols-2">
          <Panel title="Orphan tests">{d.summary.orphan_tests.length ? <p className="font-mono text-xs">{d.summary.orphan_tests.join(", ")}</p> : <p className="text-sm text-slate-600">None</p>}</Panel>
          <Panel title="Duplicate tests">{d.summary.duplicate_tests.length ? <p className="font-mono text-xs">{d.summary.duplicate_tests.join(", ")}</p> : <p className="text-sm text-slate-600">None</p>}</Panel></div>}
      </>}
    </>
  );
}

// ---------------- analytics ----------------
export function AnalyticsPage() {
  const { projectId } = useProjects();
  const q = useQuery({ queryKey: ["quality", projectId], queryFn: () => api.get<any>("/analytics/quality", { project_id: projectId }) });
  const exp = (fmt: string, report = "quality") => downloadUrl(`/exports/${report}.${fmt}`, { project_id: projectId });
  return (
    <>
      <PageHeader title="Quality Analytics" subtitle="Release readiness, coverage, defect density and regressions derived from live records."
        actions={<div className="flex items-center gap-2 text-sm"><span className="text-slate-600">Download report</span>
          {["pdf", "csv", "json", "md"].map((f) => <a key={f} className="rounded border border-slate-300 bg-white px-2 py-1 text-xs hover:bg-slate-50" href={exp(f)}>{f.toUpperCase()}</a>)}</div>} />
      {q.error ? <ErrorState error={q.error} onRetry={q.refetch} /> : !q.data ? <LoadingBlock rows={8} /> : <>
        <Panel title="Release quality summary" bodyClass="p-0" className="mb-4"><div className="overflow-x-auto"><table className="w-full text-sm">
          <thead className="bg-slate-50 text-xs text-slate-600"><tr>{["Project", "Readiness", "Requirement coverage", "Automation coverage", "Approved tests", "Open defects", "Critical open", "Defect density", "Regressions", "Impacted tests", "Last execution"].map((h) =>
            <th key={h} className="whitespace-nowrap px-3 py-2 text-left font-medium">{h}</th>)}</tr></thead>
          <tbody>{q.data.projects.map((p: any) => <tr key={p.project} className="border-t border-slate-100">
            <td className="px-3 py-2 font-medium">{p.name}</td>
            <td className="px-3 py-2"><Badge value={p.release_readiness === "ready" ? "passed" : p.release_readiness === "blocked" ? "failed" : "pending_review"}>{label(p.release_readiness)}</Badge></td>
            <td className="px-3 py-2 tabular-nums">{pct(p.requirement_coverage_pct)}</td><td className="px-3 py-2 tabular-nums">{pct(p.automation_coverage_pct)}</td>
            <td className="px-3 py-2 tabular-nums">{p.approved_tests}/{p.tests}</td><td className="px-3 py-2 tabular-nums">{p.open_defects}</td>
            <td className="px-3 py-2 tabular-nums">{p.critical_open}</td><td className="px-3 py-2 tabular-nums">{p.defect_density_per_requirement} per req.</td>
            <td className="px-3 py-2 tabular-nums">{p.regressions}</td><td className="px-3 py-2 tabular-nums">{p.impacted_tests}</td>
            <td className="px-3 py-2">{p.last_execution ? <><Badge value={p.last_execution.status} /> <span className="text-xs text-slate-500">HCM {p.last_execution.hcm_version}</span></> : "—"}</td></tr>)}</tbody></table></div></Panel>
        <div className="grid gap-4 lg:grid-cols-2">
          <Panel title="Open defect ageing" bodyClass="h-64"><ResponsiveContainer><BarChart data={q.data.projects.map((p: any) => ({ project: p.project, ...p.defect_ageing }))} margin={{ left: -10 }}>
            <CartesianGrid stroke="#e2e8f0" vertical={false} /><XAxis dataKey="project" tick={{ fontSize: 11 }} /><YAxis allowDecimals={false} tick={{ fontSize: 11 }} /><Tooltip />
            {[["0-7d", "#94a3b8"], ["8-30d", "#d97706"], ["31-90d", "#ea580c"], [">90d", "#b91c1c"]].map(([k, c]) => <Bar key={k} dataKey={k} stackId="a" fill={c} name={k} />)}
          </BarChart></ResponsiveContainer></Panel>
          <Panel title="Coverage by project" bodyClass="h-64"><ResponsiveContainer><BarChart data={q.data.projects} margin={{ left: -10 }}>
            <CartesianGrid stroke="#e2e8f0" vertical={false} /><XAxis dataKey="project" tick={{ fontSize: 11 }} /><YAxis unit="%" domain={[0, 100]} tick={{ fontSize: 11 }} /><Tooltip />
            <Bar dataKey="requirement_coverage_pct" name="Requirement coverage" fill="#1f4fbf" /><Bar dataKey="automation_coverage_pct" name="Automation coverage" fill="#93c5fd" />
          </BarChart></ResponsiveContainer></Panel>
        </div>
        <Panel title="Other exports" className="mt-4"><div className="flex flex-wrap gap-4 text-sm">
          {[["Defect register", "defects"], ["Traceability matrix", "traceability"], ["Execution history", "executions"]].map(([n, r]) =>
            <span key={r} className="flex items-center gap-2">{n}{["csv", "json", "md", "pdf"].map((f) => <a key={f} className="text-accent hover:underline" href={exp(f, r)}>{f.toUpperCase()}</a>)}</span>)}</div></Panel>
      </>}
    </>
  );
}

// ---------------- evaluations ----------------
export function EvaluationsPage() {
  const q = useQuery({ queryKey: ["evals"], queryFn: () => api.get<any>("/evaluations") });
  const cfg = useQuery({ queryKey: ["config"], queryFn: () => api.get<any>("/config") });
  const [sel, setSel] = useState<number | null>(null);
  const detail = useQuery({ queryKey: ["eval", sel], enabled: !!sel, queryFn: () => api.get<any>(`/evaluations/${sel}`) });
  const [provider, setProvider] = useState("groq");
  const [runId, setRunId] = useState<number | null>(null);
  const { can } = useAuth();
  const toast = useToast();
  const run = useMutation({ mutationFn: () => api.post<any>("/evaluations/run", { provider }), onSuccess: (r) => { setRunId(r.run_id); setSel(r.eval_run_id); }, onError: toast.error });
  const providers = cfg.data?.llm?.providers ?? [];
  const configured = provider === "mock" || providers.find((p: any) => p.name === provider)?.configured;
  const M = [["clause_coverage", "Clause coverage", true], ["ungrounded_rate", "Ungrounded output rate", false], ["duplicate_rate", "Duplicate test rate", false],
    ["schema_pass_rate", "Schema pass rate", true], ["ambiguity_recall", "Ambiguity recall", true], ["traceability", "Traceability", true],
    ["avg_retries", "Average repair attempts", false], ["failure_classification_accuracy", "Failure classification accuracy", true]] as const;
  return (
    <>
      <PageHeader title="AI Evaluations" subtitle={`Measure AI quality against ${q.data?.scenarios.length ?? "the"} golden HCM scenarios. Scores are computed from real runs only.`}
        actions={can("eval.run") && <>
          <Select className="w-56" value={provider} onChange={(e) => setProvider(e.target.value)} aria-label="Provider">
            {providers.map((p: any) => <option key={p.name} value={p.name}>{label(p.name)} ({p.model}){p.configured ? "" : ", not configured"}</option>)}
            <option value="mock">Fixture provider (CI baseline)</option></Select>
          <Button variant="primary" disabled={!configured} loading={run.isPending} onClick={() => run.mutate()}>Run evaluation</Button></>} />
      {runId && <Panel title="Evaluation in progress" className="mb-4"><RunProgress runId={runId} onDone={() => { q.refetch(); detail.refetch(); }} /></Panel>}
      {q.error ? <ErrorState error={q.error} onRetry={q.refetch} /> : !q.data ? <LoadingBlock /> : !q.data.runs.length ?
        <Panel><EmptyState title="No evaluations have been run" body={configured ? "Run an evaluation to measure grounding, coverage and schema compliance." :
          "Configure Groq or Gemini to evaluate a real model, or run the fixture baseline used in CI."}
          action={can("eval.run") ? <Button variant="primary" disabled={!configured} onClick={() => run.mutate()}>Run evaluation</Button> : undefined} /></Panel> :
        <div className="grid gap-4 xl:grid-cols-3">
          <Panel title="History" bodyClass="p-0"><ul className="divide-y divide-slate-100">{q.data.runs.map((r: any) => (
            <li key={r.id}><button onClick={() => setSel(r.id)} className={cn("w-full px-4 py-2.5 text-left text-sm hover:bg-slate-50", sel === r.id && "bg-accent-soft")}>
              <span className="flex items-center gap-2">#{r.id} {label(r.provider)} <Badge value={r.status} />{r.is_fixture && <Badge>Fixture</Badge>}</span>
              <span className="text-xs text-slate-500">{r.model}, {fmtDate(r.started_at)}</span></button></li>))}</ul></Panel>
          <div className="space-y-4 xl:col-span-2">{!sel ? <Panel><EmptyState title="Select an evaluation run" /></Panel> : !detail.data ? <LoadingBlock /> : <>
            {detail.data.is_fixture && <Notice>Fixture results come from the deterministic mock provider used in CI. They validate the harness, not a real model.</Notice>}
            {detail.data.error && <Notice tone="danger">{detail.data.error}</Notice>}
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">{M.map(([k, n]) => { const v = detail.data.metrics?.[k];
              return <Stat key={k} label={n} value={v === null || v === undefined ? "—" : k === "avg_retries" ? v.toFixed(2) : `${(v * 100).toFixed(0)}%`} />; })}</div>
            <Panel title="Scenarios" bodyClass="p-0"><table className="w-full text-sm"><tbody>{detail.data.results.map((r: any) => (
              <tr key={r.scenario} className="border-t border-slate-100 first:border-0"><td className="px-3 py-2 font-mono text-xs">{r.scenario}</td>
                <td className="px-3 py-2"><Badge value={r.passed ? "passed" : "failed"} /></td>
                <td className="px-3 py-2 text-xs text-slate-600">{r.metrics.error ?? `coverage ${r.metrics.clause_coverage}, ungrounded ${r.metrics.ungrounded_rate ?? "—"}, tests ${r.metrics.tests_generated}, edge cases ${r.metrics.edge_cases_found}`}
                  {r.metrics.forbidden_outputs?.length > 0 && <span className="text-red-700">, forbidden output present</span>}</td></tr>))}</tbody></table></Panel></>}
          </div>
        </div>}
    </>
  );
}

// ---------------- audit ----------------
export function AuditPage() {
  const { projectId } = useProjects();
  const st = useListState(["project_id", "entity_type", "source"], { sort: "created_at" });
  const pid = st.filters.project_id || (projectId ? String(projectId) : "");
  const params = { ...st.params, ...(pid ? { project_id: pid } : {}) };
  const q = useQuery({ queryKey: ["audit", params], queryFn: () => api.get<Page<AuditEntry>>("/audit", params) });
  const [open, setOpen] = useState<AuditEntry | null>(null);
  return (
    <>
      <PageHeader title="Audit Logs" subtitle="An append-only record of every state-changing operation, with trace IDs for investigation." />
      <div className="mb-2"><FilterChips state={st} /></div>
      <div className="grid gap-4 xl:grid-cols-3">
        <div className="min-w-0 xl:col-span-2"><DataTable query={q} state={st} onRowClick={setOpen}
          toolbar={<>
            <Input placeholder="Search action or record" className="w-60" defaultValue={st.q} aria-label="Search audit" onKeyDown={(e) => e.key === "Enter" && st.setQ((e.target as HTMLInputElement).value)} />
            <Select className="w-44" value={st.filters.entity_type} onChange={(e) => st.setFilter("entity_type", e.target.value)} aria-label="Record type">
              <option value="">Any record type</option>{["requirement", "test_case", "execution", "defect", "project", "user", "integration", "eval_run"].map((s) => <option key={s} value={s}>{label(s)}</option>)}</Select>
            <Select className="w-40" value={st.filters.source} onChange={(e) => st.setFilter("source", e.target.value)} aria-label="Source">
              <option value="">Any source</option><option value="platform">Platform</option><option value="seed_import">Historical import</option><option value="ci">CI</option></Select></>}
          columns={[
            { id: "at", header: "When", sortKey: "created_at", cell: (a) => <span className="whitespace-nowrap text-slate-600">{fmtDate(a.created_at)}</span> },
            { id: "actor", header: "Actor", cell: (a) => a.actor?.name ?? <span className="text-slate-400">System</span> },
            { id: "action", header: "Action", sortKey: "action", cell: (a) => <span className="font-mono text-xs">{a.action}</span> },
            { id: "rec", header: "Record", cell: (a) => <Key>{a.entity_key ?? `${a.entity_type} ${a.entity_id ?? ""}`}</Key> },
            { id: "src", header: "Source", cell: (a) => label(a.source === "seed_import" ? "historical_import" : a.source) },
          ]} /></div>
        <Panel title="Entry detail" className="h-fit">{!open ? <p className="text-sm text-slate-600">Select an entry.</p> : <div className="space-y-3">
          <KV items={[["Action", open.action], ["Record", `${open.entity_type} ${open.entity_key ?? open.entity_id ?? ""}`], ["Actor", open.actor?.name ?? "System"],
            ["When", fmtDate(open.created_at)], ["Trace ID", <span className="font-mono text-xs">{open.trace_id ?? "—"}</span>]]} />
          <Code>{JSON.stringify(open.details, null, 2)}</Code></div>}</Panel>
      </div>
    </>
  );
}

// ---------------- integrations ----------------
export function IntegrationsPage() {
  const q = useQuery({ queryKey: ["integrations"], queryFn: () => api.get<any>("/integrations") });
  const { can } = useAuth();
  const toast = useToast();
  const [edit, setEdit] = useState<Record<number, { repo: string; branch: string }>>({});
  const save = useMutation({ mutationFn: ({ pid, v }: { pid: number; v: { repo: string; branch: string } }) => api.put<any>(`/integrations/github/${pid}`, v),
    onSuccess: (r) => { q.refetch(); toast.ok(r.detail); }, onError: toast.error });
  const exportTests = useMutation({ mutationFn: (pid: number) => api.post<any>(`/integrations/github/${pid}/export-tests`), onSuccess: (r) => toast.ok(`Exported ${r.exported.length} test files`), onError: toast.error });
  if (q.error) return <ErrorState error={q.error} onRetry={q.refetch} />;
  if (!q.data) return <LoadingBlock rows={6} />;
  return (
    <>
      <PageHeader title="Integrations" subtitle="Connect GitHub for issues and test export, and ingest CI results. Both are optional." />
      <div className="mb-4 grid gap-3 md:grid-cols-2">
        <Notice tone={q.data.github_token_configured ? "info" : "warn"}>{q.data.github_token_configured ? "A GitHub token is configured on the server." :
          "GITHUB_TOKEN is not set. Repository settings can be saved, but nothing is sent to GitHub. Defects can still be downloaded as Markdown or JSON."}</Notice>
        <Notice tone={q.data.ci_ingest_configured ? "info" : "warn"}>{q.data.ci_ingest_configured ? "CI result ingestion is enabled (POST /api/v1/ci/results)." :
          "TRACETEST_CI_TOKEN is not set, so CI result ingestion is disabled. See docs/EXECUTION_ENGINE.md."}</Notice>
      </div>
      <Panel title="GitHub repositories" bodyClass="p-0"><table className="w-full text-sm"><thead className="bg-slate-50 text-xs text-slate-600"><tr>
        {["Project", "Repository", "Branch", "Status", ""].map((h) => <th key={h} className="px-3 py-2 text-left font-medium">{h}</th>)}</tr></thead>
        <tbody>{q.data.projects.map(({ project, github }: any) => { const v = edit[project.id] ?? { repo: github?.config?.repo ?? "", branch: github?.config?.branch ?? "main" };
          return <tr key={project.id} className="border-t border-slate-100">
            <td className="px-3 py-2 font-medium">{project.name}</td>
            <td className="px-3 py-2"><Input className="h-8" placeholder="owner/repo" value={v.repo} disabled={!can("project.admin")} aria-label={`${project.key} repository`} onChange={(e) => setEdit({ ...edit, [project.id]: { ...v, repo: e.target.value } })} /></td>
            <td className="px-3 py-2"><Input className="h-8 w-32" value={v.branch} disabled={!can("project.admin")} aria-label={`${project.key} branch`} onChange={(e) => setEdit({ ...edit, [project.id]: { ...v, branch: e.target.value } })} /></td>
            <td className="px-3 py-2"><Badge value={github?.status ?? "not_configured"} /></td>
            <td className="px-3 py-2 text-right">{can("project.admin") && <span className="flex justify-end gap-2">
              <Button size="sm" disabled={!/^[\w.-]+\/[\w.-]+$/.test(v.repo)} onClick={() => save.mutate({ pid: project.id, v })}>Save and verify</Button>
              <Button size="sm" disabled={github?.status !== "connected"} onClick={() => exportTests.mutate(project.id)}>Export approved tests</Button></span>}</td></tr>; })}</tbody></table></Panel>
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Panel title="Recent integration events" bodyClass="p-0">{!q.data.events.length ? <EmptyState title="No integration activity yet" /> :
          <ul className="divide-y divide-slate-100">{q.data.events.map((e: any, i: number) => <li key={i} className="px-4 py-2 text-sm"><span className="flex items-center gap-2">{label(e.kind)} <Badge value={e.status === "ok" ? "passed" : e.status} /></span>
            <p className="text-xs text-slate-600">{e.request}: {e.response}</p><p className="text-2xs text-slate-400">{fmtDate(e.at)}</p></li>)}</ul>}</Panel>
        <Panel title="CI executions" bodyClass="p-0">{!q.data.ci_executions.length ? <EmptyState title="No CI results received" body="The bundled GitHub Actions workflow posts junit results here when TRACETEST_CI_TOKEN and TRACETEST_URL are set." /> :
          <ul className="divide-y divide-slate-100">{q.data.ci_executions.map((e: any) => <li key={e.id} className="px-4 py-2 text-sm"><Link className="font-mono text-xs text-accent" to={`/executions/${e.id}`}>{e.key}</Link> <Badge value={e.status} /> <span className="text-xs text-slate-500">{e.branch} {e.commit_sha?.slice(0, 7)}</span></li>)}</ul>}</Panel>
      </div>
    </>
  );
}

// ---------------- settings ----------------
export function SettingsPage() {
  const cfg = useQuery({ queryKey: ["config"], queryFn: () => api.get<any>("/config") });
  const health = useQuery({ queryKey: ["health"], queryFn: () => api.get<any>("/health") });
  const { can, me } = useAuth();
  const admin = can("user.admin");
  const users = useQuery({ queryKey: ["users", "all"], enabled: admin, queryFn: () => api.get<Page<User>>("/users", { page_size: 200 }) });
  const toast = useToast();
  const qc = useQueryClient();
  const [nu, setNu] = useState({ email: "", full_name: "", role: "qa_engineer" });
  const create = useMutation({ mutationFn: () => api.post("/users", { email: nu.email, full_name: nu.full_name, roles: [nu.role] }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["users"] }); setNu({ email: "", full_name: "", role: "qa_engineer" }); toast.ok("User added without sign-in access"); }, onError: toast.error });
  const upd = useMutation({ mutationFn: ({ id, body }: { id: number; body: any }) => api.patch(`/users/${id}`, body), onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }), onError: toast.error });
  const backup = useMutation({ mutationFn: () => api.post<any>("/admin/backup"), onSuccess: (r) => toast.ok(`Backup written: ${r.backup}`), onError: toast.error });
  const c = cfg.data;
  return (
    <>
      <PageHeader title="Settings" subtitle="AI providers, execution sandbox, system health and user management." />
      {!c ? <LoadingBlock rows={6} /> : <div className="grid gap-4 xl:grid-cols-2">
        <Panel title="AI providers">
          {!c.llm.any_configured && <div className="mb-3"><Notice tone="warn">No AI provider is configured. Set GROQ_API_KEY (primary) or GEMINI_API_KEY (backup)
            in the server environment and restart. The rest of the application works without them.</Notice></div>}
          {c.llm.mode === "mock" && <div className="mb-3"><Notice>Fixture mode is enabled (TRACETEST_LLM_MODE=mock). AI output comes from deterministic fixtures and is labelled as such.</Notice></div>}
          <table className="w-full text-sm"><tbody>{c.llm.providers.map((p: any, i: number) => <tr key={p.name} className="border-t border-slate-100 first:border-0">
            <td className="py-2 pr-3">{i === 0 ? "Primary" : i === 1 ? "Backup" : "Local"}</td><td className="py-2 pr-3 font-medium">{label(p.name)}</td>
            <td className="py-2 pr-3 font-mono text-xs">{p.model}</td><td className="py-2 pr-3"><Badge value={p.configured ? "connected" : "not_configured"}>{p.configured ? "Configured" : "Not configured"}</Badge></td>
            <td className="py-2 text-xs text-slate-500">circuit {p.circuit}</td></tr>)}</tbody></table>
          <p className="mt-2 text-xs text-slate-500">Keys are never displayed. Fallback order: Groq, then Gemini, then an explicit failure state.</p>
        </Panel>
        <Panel title="System">
          <KV items={[["Environment", c.environment], ["Database", health.data ? `${health.data.database.integrity}, ${health.data.database.journal_mode.toUpperCase()} journal, ${health.data.database.foreign_key_violations} FK violations` : "…"],
            ["Data directory", c.data_dir ?? "Visible to administrators"], ["Sandbox timeout", `${c.sandbox.timeout_seconds} s`], ["Sandbox memory", `${c.sandbox.memory_mb} MB`],
            ["Output limit", `${Math.round(c.sandbox.max_output_bytes / 1024)} KB`], ["Playwright target", c.playwright_target_url ?? "Not configured"],
            ["Records", `${c.counts.requirements} requirements, ${c.counts.test_cases} tests, ${c.counts.executions} executions, ${c.counts.defects} defects`]]} />
          {admin && <Button className="mt-3" onClick={() => backup.mutate()} loading={backup.isPending}>Back up database</Button>}
        </Panel>
        <Panel title="Your account"><KV items={[["Name", me?.user.full_name], ["Email", me?.user.email], ["Roles", me?.roles.map(label).join(", ")]]} /></Panel>
        {admin && <Panel title="Users" className="xl:col-span-2" bodyClass="p-0">
          <table className="w-full text-sm"><thead className="bg-slate-50 text-xs text-slate-600"><tr>{["Name", "Email", "Roles", "Sign-in", "Active"].map((h) => <th key={h} className="px-3 py-2 text-left font-medium">{h}</th>)}</tr></thead>
            <tbody>{users.data?.items.map((u) => <tr key={u.id} className="border-t border-slate-100">
              <td className="px-3 py-2 font-medium">{u.full_name}<p className="text-xs font-normal text-slate-500">{u.title}</p></td><td className="px-3 py-2">{u.email}</td>
              <td className="px-3 py-2"><Select className="h-8 w-40" value={u.roles[0]} onChange={(e) => upd.mutate({ id: u.id, body: { roles: [e.target.value] } })} aria-label={`Role for ${u.full_name}`}>
                {["admin", "qa_engineer", "reviewer"].map((r) => <option key={r} value={r}>{label(r)}</option>)}</Select></td>
              <td className="px-3 py-2 text-xs">{u.can_login ? "Enabled" : "Directory only"}</td>
              <td className="px-3 py-2"><input type="checkbox" checked={u.is_active} disabled={u.id === me?.user.id} aria-label={`Active ${u.full_name}`} onChange={(e) => upd.mutate({ id: u.id, body: { is_active: e.target.checked } })} /></td></tr>)}</tbody></table>
          <div className="grid gap-2 border-t border-slate-200 p-3 sm:grid-cols-4">
            <Field label="Full name" htmlFor="nn"><Input id="nn" value={nu.full_name} onChange={(e) => setNu({ ...nu, full_name: e.target.value })} /></Field>
            <Field label="Email" htmlFor="ne"><Input id="ne" value={nu.email} onChange={(e) => setNu({ ...nu, email: e.target.value })} /></Field>
            <Field label="Role" htmlFor="nr"><Select id="nr" value={nu.role} onChange={(e) => setNu({ ...nu, role: e.target.value })}>{["admin", "qa_engineer", "reviewer"].map((r) => <option key={r} value={r}>{label(r)}</option>)}</Select></Field>
            <div className="flex items-end"><Button disabled={nu.full_name.length < 2 || !nu.email.includes("@")} loading={create.isPending} onClick={() => create.mutate()}>Add user</Button></div>
          </div></Panel>}
      </div>}
    </>
  );
}
