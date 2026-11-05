import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { DataTable } from "@/components/DataTable";
import { useToast } from "@/components/Toast";
import { Badge, Button, Dialog, ErrorState, Field, Input, KV, LoadingBlock, PageHeader, Panel, Select, Stat, Tabs, Textarea } from "@/components/ui";
import { useAuth } from "@/hooks/useAuth";
import { useListState } from "@/hooks/useListState";
import { useProjects } from "@/hooks/useProjects";
import { api, type Schemas } from "@/services/api";
import type { Page, Project, User } from "@/types/models";
import { fmtDate, pct } from "@/utils/format";

export function ProjectsPage() {
  const st = useListState(["status"], { sort: "key", order: "asc" });
  const nav = useNavigate();
  const { can } = useAuth();
  const q = useQuery({ queryKey: ["projects", st.params], queryFn: () => api.get<Page<Project>>("/projects", st.params) });
  const [open, setOpen] = useState(false);
  return (
    <>
      <PageHeader title="Projects" subtitle="Business domains under test, each with its own requirements, environments and team."
        actions={can("project.admin") && <Button variant="primary" onClick={() => setOpen(true)}>New project</Button>} />
      <DataTable query={q} state={st} onRowClick={(p) => nav(`/projects/${p.id}`)}
        toolbar={<><Input placeholder="Search projects" className="w-60" defaultValue={st.q} onKeyDown={(e) => e.key === "Enter" && st.setQ((e.target as HTMLInputElement).value)} />
          <Select className="w-40" value={st.filters.status} onChange={(e) => st.setFilter("status", e.target.value)} aria-label="Status">
            <option value="">Any status</option><option value="active">Active</option><option value="archived">Archived</option></Select></>}
        columns={[
          { id: "key", header: "Key", sortKey: "key", cell: (p) => <span className="font-mono text-xs">{p.key}</span> },
          { id: "name", header: "Project", sortKey: "name", cell: (p) => <><p className="font-medium">{p.name}</p><p className="text-xs text-slate-500">{p.description}</p></> },
          { id: "status", header: "Status", cell: (p) => <Badge value={p.status} /> },
          { id: "req", header: "Requirements", cell: (p) => p.stats.requirements, className: "tabular-nums" },
          { id: "tests", header: "Tests", cell: (p) => p.stats.tests, className: "tabular-nums" },
          { id: "cov", header: "Coverage", cell: (p) => pct(p.stats.coverage_pct), className: "tabular-nums" },
          { id: "def", header: "Open defects", cell: (p) => p.stats.open_defects, className: "tabular-nums" },
        ]} />
      <ProjectDialog open={open} onOpenChange={setOpen} />
    </>
  );
}

function ProjectDialog({ open, onOpenChange, project }: { open: boolean; onOpenChange: (o: boolean) => void; project?: Project }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [f, setF] = useState({ key: project?.key ?? "", name: project?.name ?? "", description: project?.description ?? "" });
  const m = useMutation({
    mutationFn: () => project ? api.patch(`/projects/${project.id}`, { name: f.name, description: f.description })
      : api.post("/projects", f satisfies Schemas["ProjectIn"]),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["projects"] }); toast.ok(project ? "Project updated" : "Project created"); onOpenChange(false); },
    onError: toast.error,
  });
  const keyOk = /^[A-Za-z]{2,6}$/.test(f.key);
  return (
    <Dialog open={open} onOpenChange={onOpenChange} title={project ? "Edit project" : "New project"}
      footer={<><Button onClick={() => onOpenChange(false)}>Cancel</Button>
        <Button variant="primary" loading={m.isPending} disabled={f.name.length < 3 || (!project && !keyOk)} onClick={() => m.mutate()}>
          {project ? "Save changes" : "Create project"}</Button></>}>
      {!project && <Field label="Key" htmlFor="pk" hint="2–6 letters, used as the prefix for record IDs" error={f.key && !keyOk ? "Use 2–6 letters" : undefined}>
        <Input id="pk" value={f.key} onChange={(e) => setF({ ...f, key: e.target.value.toUpperCase() })} /></Field>}
      <Field label="Name" htmlFor="pn"><Input id="pn" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></Field>
      <Field label="Description" htmlFor="pd"><Textarea id="pd" rows={3} value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} /></Field>
    </Dialog>
  );
}

export function ProjectDetailPage() {
  const { id } = useParams();
  const { can } = useAuth();
  const qc = useQueryClient();
  const toast = useToast();
  const { setProjectId } = useProjects();
  const q = useQuery({ queryKey: ["project", id], queryFn: () => api.get<Project>(`/projects/${id}`) });
  const users = useQuery({ queryKey: ["users"], enabled: can("project.admin"), queryFn: () => api.get<Page<User>>("/users", { page_size: 200 }) });
  const [edit, setEdit] = useState(false);
  const [member, setMember] = useState("");
  const [env, setEnv] = useState({ name: "", kind: "reference_hcm", hcm_version: "1.1", base_url: "" });
  const [mod, setMod] = useState({ code: "", name: "" });
  const inv = () => qc.invalidateQueries({ queryKey: ["project", id] });
  const act = useMutation({ mutationFn: (fn: () => Promise<unknown>) => fn(), onSuccess: () => { inv(); toast.ok("Saved"); }, onError: toast.error });
  if (q.error) return <ErrorState error={q.error} onRetry={q.refetch} />;
  if (!q.data) return <LoadingBlock rows={8} />;
  const p = q.data;
  const admin = can("project.admin");
  return (
    <>
      <PageHeader title={<span className="flex items-center gap-2">{p.name}<Badge value={p.status} /></span>} subtitle={p.description}
        actions={<>
          <Button onClick={() => setProjectId(p.id)}>Focus workspace on this project</Button>
          {admin && <Button onClick={() => setEdit(true)}>Edit</Button>}
          {admin && <Button variant={p.status === "active" ? "danger" : "secondary"} onClick={() => act.mutate(() =>
            api.patch(`/projects/${p.id}`, { status: p.status === "active" ? "archived" : "active" }))}>
            {p.status === "active" ? "Archive project" : "Restore project"}</Button>}</>} />
      <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-5">
        <Stat label="Requirements" value={p.stats.requirements} />
        <Stat label="Test cases" value={p.stats.tests} />
        <Stat label="Suites" value={p.stats.suites} />
        <Stat label="Coverage" value={pct(p.stats.coverage_pct)} />
        <Stat label="Open defects" value={p.stats.open_defects} />
      </div>
      <Tabs tabs={[
        { value: "overview", label: "Overview", content: <div className="grid gap-4 lg:grid-cols-2">
          <Panel title="Modules" bodyClass="p-0">
            <ul className="divide-y divide-slate-100">{p.modules?.map((m) => <li key={m.id} className="px-4 py-2 text-sm">
              <span className="font-mono text-xs text-slate-500">{m.code}</span> <span className="font-medium">{m.name}</span>
              <p className="text-xs text-slate-500">{m.description}</p></li>)}</ul>
            {admin && <div className="flex gap-2 border-t border-slate-200 p-3">
              <Input placeholder="Code" className="w-24" value={mod.code} onChange={(e) => setMod({ ...mod, code: e.target.value })} aria-label="Module code" />
              <Input placeholder="Module name" value={mod.name} onChange={(e) => setMod({ ...mod, name: e.target.value })} aria-label="Module name" />
              <Button disabled={mod.code.length < 2 || mod.name.length < 2} onClick={() => act.mutate(() => api.post(`/projects/${p.id}/modules`, mod).then(() => setMod({ code: "", name: "" })))}>Add</Button></div>}
          </Panel>
          <Panel title="Environments" bodyClass="p-0">
            <ul className="divide-y divide-slate-100">{p.environments?.map((e) => <li key={e.id} className="flex items-center justify-between px-4 py-2 text-sm">
              <span>{e.name}{e.is_default && <span className="ml-2 text-xs text-slate-500">default</span>}</span>
              <span className="text-xs text-slate-500">{e.kind === "web" ? e.base_url : `Reference HCM ${e.hcm_version}`}</span></li>)}</ul>
            {admin && <div className="grid grid-cols-2 gap-2 border-t border-slate-200 p-3 sm:grid-cols-4">
              <Input placeholder="Name" value={env.name} onChange={(e) => setEnv({ ...env, name: e.target.value })} aria-label="Environment name" />
              <Select value={env.kind} onChange={(e) => setEnv({ ...env, kind: e.target.value })} aria-label="Kind">
                <option value="reference_hcm">Reference HCM</option><option value="web">Web (Playwright)</option></Select>
              {env.kind === "web" ? <Input placeholder="https://…" value={env.base_url} onChange={(e) => setEnv({ ...env, base_url: e.target.value })} aria-label="Base URL" />
                : <Select value={env.hcm_version} onChange={(e) => setEnv({ ...env, hcm_version: e.target.value })} aria-label="HCM version">
                  <option value="1.0">1.0</option><option value="1.1">1.1</option></Select>}
              <Button disabled={env.name.length < 2} onClick={() => act.mutate(() => api.post(`/projects/${p.id}/environments`,
                env.kind === "web" ? { name: env.name, kind: "web", base_url: env.base_url } : { name: env.name, kind: env.kind, hcm_version: env.hcm_version }))}>Add</Button></div>}
          </Panel>
        </div> },
        { value: "members", label: `Members (${p.members?.length ?? 0})`, content: <Panel bodyClass="p-0">
          <table className="w-full text-sm"><tbody>{p.members?.map((m) => <tr key={m.user.id} className="border-b border-slate-100">
            <td className="px-4 py-2 font-medium">{m.user.full_name}</td><td className="px-4 py-2 text-slate-600">{m.user.title}</td>
            <td className="px-4 py-2">{m.user.roles.map((r) => <Badge key={r} value={r} className="mr-1" />)}</td>
            <td className="px-4 py-2 text-right">{admin && <Button size="sm" variant="ghost" onClick={() => act.mutate(() => api.delete(`/projects/${p.id}/members/${m.user.id}`))}>Remove</Button>}</td>
          </tr>)}</tbody></table>
          {admin && <div className="flex gap-2 border-t border-slate-200 p-3">
            <Select value={member} onChange={(e) => setMember(e.target.value)} aria-label="User to add" className="max-w-xs">
              <option value="">Select a user</option>
              {users.data?.items.filter((u) => !p.members?.some((m) => m.user.id === u.id)).map((u) => <option key={u.id} value={u.id}>{u.full_name}</option>)}
            </Select>
            <Button disabled={!member} onClick={() => act.mutate(() => api.post(`/projects/${p.id}/members`, { user_id: Number(member) }).then(() => setMember("")))}>Add member</Button></div>}
        </Panel> },
        { value: "records", label: "Linked records", content: <Panel>
          <KV items={[["Requirements", <Link className="text-accent hover:underline" to={`/requirements?project_id=${p.id}`}>{p.stats.requirements} requirements</Link>],
            ["Test cases", <Link className="text-accent hover:underline" to={`/tests?project_id=${p.id}`}>{p.stats.tests} tests</Link>],
            ["Suites", <Link className="text-accent hover:underline" to={`/suites?project_id=${p.id}`}>{p.stats.suites} suites</Link>],
            ["Defects", <Link className="text-accent hover:underline" to={`/defects?project_id=${p.id}`}>{p.stats.open_defects} open</Link>],
            ["Traceability", <Link className="text-accent hover:underline" to={`/traceability?project_id=${p.id}`}>Open matrix</Link>],
            ["Created", fmtDate((p as any).created_at)]]} />
        </Panel> },
      ]} />
      {edit && <ProjectDialog open={edit} onOpenChange={setEdit} project={p} />}
    </>
  );
}
