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
  const [repoOpen, setRepoOpen] = useState(false);
  return (
    <>
      <PageHeader title="Projects" subtitle="Software projects and repositories under verification, each with isolated requirements, environments, and execution evidence."
        actions={
          <div className="flex items-center gap-2">
            <Button variant="primary" onClick={() => setRepoOpen(true)}>Connect GitHub Repository</Button>
            {can("project.admin") && <Button onClick={() => setOpen(true)}>New project</Button>}
          </div>
        } />
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
      <ConnectRepoDialog open={repoOpen} onOpenChange={setRepoOpen} />
    </>
  );
}

export function ConnectRepoDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const { setProjectId } = useProjects();
  const [f, setF] = useState({
    repo_url: "https://github.com/sohan10012/EchoBox.git",
    branch: "main",
    commit_sha: "",
    project_key: "",
    project_name: "",
    auth_token: "",
  });

  const m = useMutation({
    mutationFn: () =>
      api.post<any>("/projects/import-repo", {
        repo_url: f.repo_url,
        branch: f.branch || "main",
        commit_sha: f.commit_sha || null,
        project_key: f.project_key || null,
        project_name: f.project_name || null,
        auth_token: f.auth_token || null,
        dry_run: false,
      }),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      if (data?.project?.id) {
        setProjectId(data.project.id);
      }
      toast.ok(`Repository ${f.repo_url} connected and analyzed successfully!`);
      onOpenChange(false);
    },
    onError: (err: any) => toast.error(err?.message || "Failed to connect repository"),
  });

  const urlValid = /^https:\/\/github\.com\/[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+/.test(f.repo_url.trim());

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title="Connect GitHub Repository"
      footer={
        <>
          <Button onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button
            variant="primary"
            loading={m.isPending}
            disabled={!urlValid}
            onClick={() => m.mutate()}
          >
            Import & Analyze
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        <p className="text-xs text-slate-500">
          Connect a public or private GitHub repository to analyze source code, extract requirements with provenance, and generate traceable test cases.
        </p>
        <Field label="GitHub Repository URL" htmlFor="r_url" hint="Format: https://github.com/owner/repository" error={f.repo_url && !urlValid ? "Must be a valid https://github.com/owner/repo URL" : undefined}>
          <Input id="r_url" placeholder="https://github.com/owner/repo" value={f.repo_url} onChange={(e) => setF({ ...f, repo_url: e.target.value })} />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Default Branch" htmlFor="r_branch">
            <Input id="r_branch" placeholder="main" value={f.branch} onChange={(e) => setF({ ...f, branch: e.target.value })} />
          </Field>
          <Field label="Pin Exact Commit (Optional)" htmlFor="r_sha">
            <Input id="r_sha" placeholder="Full or short SHA" value={f.commit_sha} onChange={(e) => setF({ ...f, commit_sha: e.target.value })} />
          </Field>
        </div>
        <Field label="Private Repository Token (Optional)" htmlFor="r_token" hint="Personal Access Token with repo read permission for private repositories. Never exposed to browser logs.">
          <Input id="r_token" type="password" placeholder="ghp_..." value={f.auth_token} onChange={(e) => setF({ ...f, auth_token: e.target.value })} />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Project Key (Optional)" htmlFor="r_key" hint="2–8 letters, e.g. ECHO, AUTH">
            <Input id="r_key" placeholder="Auto-derived" value={f.project_key} onChange={(e) => setF({ ...f, project_key: e.target.value.toUpperCase() })} />
          </Field>
          <Field label="Project Title (Optional)" htmlFor="r_name">
            <Input id="r_name" placeholder="Auto-derived" value={f.project_name} onChange={(e) => setF({ ...f, project_name: e.target.value })} />
          </Field>
        </div>
      </div>
    </Dialog>
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
  const keyOk = /^[A-Za-z0-9_-]{2,10}$/.test(f.key);
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
  const [repoOpen, setRepoOpen] = useState(false);
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
        { value: "github", label: "GitHub Repository", content: <Panel title="Connected Source Repository">
          {(p as any).github ? (
            <div className="space-y-4">
              <KV items={[
                ["Repository", <a href={(p as any).github.url} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline font-mono text-xs">{(p as any).github.repo}</a>],
                ["Default Branch", <span className="font-mono text-xs">{(p as any).github.branch || "main"}</span>],
                ["Last Analyzed Commit", <span className="font-mono text-xs">{(p as any).github.commit_sha || "Latest"}</span>],
                ["Status", <Badge value={(p as any).github.status || "connected"} />],
              ]} />
              <div className="flex gap-2 pt-2 border-t border-slate-100">
                <Button onClick={() => act.mutate(() => api.post(`/projects/${p.id}/refresh-repo`, {}))}>Refresh Repository & AST</Button>
                <Button variant="danger" onClick={() => act.mutate(() => api.delete(`/projects/${p.id}/disconnect-repo`))}>Disconnect Repository</Button>
              </div>
            </div>
          ) : (
            <div className="py-4 text-center space-y-3">
              <p className="text-xs text-slate-500">No GitHub repository is connected to this project.</p>
              <Button variant="primary" onClick={() => setRepoOpen(true)}>Connect GitHub Repository</Button>
            </div>
          )}
        </Panel> },
      ]} />
      {edit && <ProjectDialog open={edit} onOpenChange={setEdit} project={p} />}
      <ConnectRepoDialog open={repoOpen} onOpenChange={setRepoOpen} />
    </>
  );
}
