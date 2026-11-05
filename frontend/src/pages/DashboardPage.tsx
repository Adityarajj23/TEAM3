import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge, EmptyState, ErrorState, Input, Key, LoadingBlock, PageHeader, Panel, Skeleton, Stat } from "@/components/ui";
import { useProjects } from "@/hooks/useProjects";
import { api } from "@/services/api";
import { fmtDate, label, pct } from "@/utils/format";

const STATUS_COLOR: Record<string, string> = { passed: "#16a34a", failed: "#dc2626", error: "#b45309", timed_out: "#7c3aed",
  skipped: "#94a3b8", approved: "#16a34a", pending_review: "#d97706", rejected: "#dc2626", changes_requested: "#f59e0b",
  needs_reapproval: "#7c3aed", deprecated: "#94a3b8", critical: "#b91c1c", high: "#ea580c", medium: "#d97706", low: "#94a3b8" };
const axis = { fontSize: 11, fill: "#64748b" };

export default function DashboardPage() {
  const { projectId, current } = useProjects();
  const nav = useNavigate();
  const [range, setRange] = useState({ from: "", to: "" });
  const q = useQuery({ queryKey: ["dashboard", projectId, range], queryFn: () => api.get<any>("/analytics/dashboard",
    { project_id: projectId, date_from: range.from || undefined, date_to: range.to || undefined }) });
  const d = q.data;
  const k = d?.kpis;
  const scope = projectId ? `project_id=${projectId}&` : "";
  return (
    <>
      <PageHeader title={current ? `${current.name} overview` : "Quality overview"}
        subtitle={current ? current.description : "Organisation-wide quality across all projects you can access."}
        actions={<div className="flex items-center gap-2 text-sm">
          <label className="flex items-center gap-1 text-slate-600">From<Input type="date" className="w-36" value={range.from}
            onChange={(e) => setRange({ ...range, from: e.target.value })} /></label>
          <label className="flex items-center gap-1 text-slate-600">To<Input type="date" className="w-36" value={range.to}
            onChange={(e) => setRange({ ...range, to: e.target.value })} /></label></div>} />
      {q.error ? <ErrorState error={q.error} onRetry={q.refetch} /> : (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4 2xl:grid-cols-7">
            {!k ? Array.from({ length: 7 }).map((_, i) => <Skeleton key={i} className="h-20" />) : <>
              <Stat label="Requirements" value={k.total_requirements} hint={`${k.analysed_requirements} analysed`} onClick={() => nav(`/requirements?${scope}`)} />
              <Stat label="Requirement coverage" value={pct(k.requirement_coverage)} hint="Clauses with active tests" onClick={() => nav("/traceability")} />
              <Stat label="Test cases" value={k.total_test_cases} hint={`${k.approved_test_cases} approved`} onClick={() => nav(`/tests?${scope}`)} />
              <Stat label="Pending reviews" value={k.pending_reviews} onClick={() => nav(`/tests/review?${scope}`)} />
              <Stat label="Test pass rate" value={pct(k.pass_rate)} hint={`${k.total_executions} executions in range`} onClick={() => nav(`/executions?${scope}`)} />
              <Stat label="Open defects" value={k.open_defects} hint={`${k.failed_executions} failed executions`} onClick={() => nav(`/defects?${scope}open_only=true`)} />
              <Stat label="Critical open defects" value={k.critical_defects} intent={k.critical_defects ? "bad" : "good"} onClick={() => nav(`/defects?${scope}severity=critical&open_only=true`)} />
            </>}
          </div>
          <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-3">
            <Panel title="Test execution trend" className="xl:col-span-2" bodyClass="h-64">
              {!d ? <LoadingBlock /> : !d.charts.execution_trend.length ? <EmptyState title="No executions in this range" /> :
                <ResponsiveContainer><LineChart data={d.charts.execution_trend} margin={{ left: -10, right: 8 }}>
                  <CartesianGrid stroke="#e2e8f0" vertical={false} /><XAxis dataKey="week" tick={axis} /><YAxis tick={axis} />
                  <Tooltip /><Legend wrapperStyle={{ fontSize: 12 }} />
                  <Line dataKey="passed" name="Passed results" stroke="#16a34a" strokeWidth={2} dot={false} />
                  <Line dataKey="failed" name="Failed results" stroke="#dc2626" strokeWidth={2} dot={false} />
                  <Line dataKey="error" name="Errors" stroke="#b45309" strokeWidth={1.5} dot={false} strokeDasharray="4 3" />
                </LineChart></ResponsiveContainer>}
            </Panel>
            <Panel title="Result distribution" bodyClass="h-64">
              {!d ? <LoadingBlock /> : !d.charts.result_distribution.length ? <EmptyState title="No results in this range" /> :
                <ResponsiveContainer><PieChart>
                  <Pie data={d.charts.result_distribution} dataKey="count" nameKey="status" innerRadius={55} outerRadius={85}
                    onClick={(e: any) => nav(`/executions?${scope}status=${e.status === "passed" ? "passed" : "failed"}`)}>
                    {d.charts.result_distribution.map((r: any) => <Cell key={r.status} fill={STATUS_COLOR[r.status] ?? "#94a3b8"} />)}
                  </Pie><Tooltip formatter={(v, n) => [v, label(String(n))]} /><Legend formatter={(v) => label(v)} wrapperStyle={{ fontSize: 12 }} />
                </PieChart></ResponsiveContainer>}
            </Panel>
            <Panel title="Requirement coverage by project" bodyClass="h-64">
              {!d ? <LoadingBlock /> : <ResponsiveContainer><BarChart data={d.charts.coverage_by_project} margin={{ left: -10 }}>
                <CartesianGrid stroke="#e2e8f0" vertical={false} /><XAxis dataKey="project" tick={axis} /><YAxis tick={axis} domain={[0, 100]} unit="%" />
                <Tooltip formatter={(v) => `${v}%`} /><Bar dataKey="coverage_pct" name="Coverage" fill="#1f4fbf" radius={[3, 3, 0, 0]}
                  onClick={(e: any) => nav(`/traceability?project_id=${e.project_id}`)} cursor="pointer" />
              </BarChart></ResponsiveContainer>}
            </Panel>
            <Panel title="Open defects by severity" bodyClass="h-64">
              {!d ? <LoadingBlock /> : <ResponsiveContainer><BarChart data={d.charts.defect_severity} margin={{ left: -10 }}>
                <CartesianGrid stroke="#e2e8f0" vertical={false} /><XAxis dataKey="severity" tick={axis} tickFormatter={label} /><YAxis tick={axis} allowDecimals={false} />
                <Tooltip /><Bar dataKey="count" name="Open defects" radius={[3, 3, 0, 0]} cursor="pointer"
                  onClick={(e: any) => nav(`/defects?${scope}severity=${e.severity}&open_only=true`)}>
                  {d.charts.defect_severity.map((r: any) => <Cell key={r.severity} fill={STATUS_COLOR[r.severity]} />)}</Bar>
              </BarChart></ResponsiveContainer>}
            </Panel>
            <Panel title="Defects opened and resolved" bodyClass="h-64">
              {!d ? <LoadingBlock /> : !d.charts.defect_resolution.length ? <EmptyState title="No defect activity" /> :
                <ResponsiveContainer><BarChart data={d.charts.defect_resolution} margin={{ left: -10 }}>
                  <CartesianGrid stroke="#e2e8f0" vertical={false} /><XAxis dataKey="week" tick={axis} /><YAxis tick={axis} allowDecimals={false} />
                  <Tooltip /><Legend wrapperStyle={{ fontSize: 12 }} />
                  <Bar dataKey="opened" name="Opened" fill="#ea580c" /><Bar dataKey="resolved" name="Resolved" fill="#16a34a" />
                </BarChart></ResponsiveContainer>}
            </Panel>
            <Panel title="Test case status" bodyClass="h-64">
              {!d ? <LoadingBlock /> : <ResponsiveContainer><BarChart data={d.charts.test_status} layout="vertical" margin={{ left: 30 }}>
                <XAxis type="number" tick={axis} /><YAxis type="category" dataKey="status" tick={axis} tickFormatter={label} width={110} />
                <Tooltip labelFormatter={label} /><Bar dataKey="count" name="Tests" cursor="pointer"
                  onClick={(e: any) => nav(`/tests?${scope}status=${e.status}`)}>
                  {d.charts.test_status.map((r: any) => <Cell key={r.status} fill={STATUS_COLOR[r.status] ?? "#64748b"} />)}</Bar>
              </BarChart></ResponsiveContainer>}
            </Panel>
          </div>
          <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-3">
            <Panel title="Project quality" className="xl:col-span-2" bodyClass="p-0">
              {!d ? <div className="p-4"><LoadingBlock /></div> : (
                <table className="w-full text-sm"><thead className="bg-slate-50 text-xs text-slate-600"><tr>
                  {["Project", "Coverage", "Pass rate", "Executions", "Open defects", "Critical"].map((h) =>
                    <th key={h} className="px-3 py-2 text-left font-medium">{h}</th>)}</tr></thead>
                  <tbody>{d.projects.map((p: any) => (
                    <tr key={p.project_id} className="border-t border-slate-100">
                      <td className="px-3 py-2"><Link className="text-accent hover:underline" to={`/projects/${p.project_id}`}>{p.name}</Link></td>
                      <td className="px-3 py-2 tabular-nums">{pct(p.coverage_pct)}</td><td className="px-3 py-2 tabular-nums">{pct(p.pass_rate)}</td>
                      <td className="px-3 py-2 tabular-nums">{p.executions}</td><td className="px-3 py-2 tabular-nums">{p.open_defects}</td>
                      <td className="px-3 py-2 tabular-nums">{p.critical_defects}</td></tr>))}</tbody></table>)}
            </Panel>
            <Panel title="Recent requirement changes" bodyClass="p-0">
              {!d ? <div className="p-4"><LoadingBlock /></div> : !d.recent_changes.length ? <EmptyState title="No requirement changes" /> :
                <ul className="divide-y divide-slate-100">{d.recent_changes.map((c: any) => (
                  <li key={c.key + c.version} className="px-4 py-2 text-sm">
                    <Link to={`/requirements/${c.requirement_id}?tab=versions`} className="text-ink hover:text-accent">
                      <Key>{c.key}</Key> v{c.version}</Link>
                    <p className="truncate text-slate-600">{c.summary}</p><p className="text-2xs text-slate-400">{fmtDate(c.at)}</p></li>))}</ul>}
            </Panel>
          </div>
          <Panel title="Recent execution activity" className="mt-4" bodyClass="p-0">
            {!d ? <div className="p-4"><LoadingBlock /></div> : !d.recent_executions.length ? <EmptyState title="No executions in this range" /> :
              <table className="w-full text-sm"><tbody>{d.recent_executions.map((e: any) => (
                <tr key={e.id} className="cursor-pointer border-t border-slate-100 first:border-0 hover:bg-slate-50" onClick={() => nav(`/executions/${e.id}`)}>
                  <td className="px-3 py-2"><Key>{e.key}</Key></td><td className="px-3 py-2"><Badge value={e.status} /></td>
                  <td className="px-3 py-2"><Badge value={e.source} /></td><td className="px-3 py-2 text-slate-600">Reference HCM {e.hcm_version}</td>
                  <td className="px-3 py-2 tabular-nums text-slate-600">{e.passed} passed, {e.failed} failed{e.errored ? `, ${e.errored} errors` : ""}</td>
                  <td className="px-3 py-2 text-right text-slate-500">{fmtDate(e.started_at)}</td></tr>))}</tbody></table>}
          </Panel>
        </>
      )}
    </>
  );
}
