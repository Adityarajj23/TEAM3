import * as Dropdown from "@radix-ui/react-dropdown-menu";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, BarChart3, Bell, Bug, ClipboardCheck, FileText, FlaskConical, FolderKanban, GitBranch, Grid3x3,
  LayoutDashboard, LogOut, PanelLeftClose, PanelLeftOpen, PlayCircle, ScrollText, Search, Settings } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { useProjects } from "@/hooks/useProjects";
import { api } from "@/services/api";
import { cn, fmtDate } from "@/utils/format";

const NAV = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/projects", label: "Projects", icon: FolderKanban },
  { to: "/requirements", label: "Requirements", icon: FileText },
  { to: "/tests", label: "Test Management", icon: ClipboardCheck },
  { to: "/executions", label: "Test Executions", icon: PlayCircle },
  { to: "/defects", label: "Defects", icon: Bug },
  { to: "/traceability", label: "Traceability", icon: Grid3x3 },
  { to: "/analytics", label: "Quality Analytics", icon: BarChart3 },
  { to: "/evaluations", label: "AI Evaluations", icon: FlaskConical },
  { to: "/audit", label: "Audit Logs", icon: ScrollText },
  { to: "/integrations", label: "Integrations", icon: GitBranch },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function Wordmark({ compact }: { compact?: boolean }) {
  return (
    <span className="flex items-center gap-2">
      <img src="/favicon.svg" alt="" className="h-6 w-6" />
      {!compact && <span className="text-[15px] font-semibold tracking-tight text-ink">TraceTest<span className="font-normal text-slate-500"> AI</span></span>}
    </span>
  );
}

function Breadcrumbs() {
  const { pathname } = useLocation();
  const parts = pathname.split("/").filter(Boolean);
  const nav = NAV.find((n) => n.to !== "/" && pathname.startsWith(n.to));
  if (!parts.length) return <span className="text-sm text-slate-600">Overview</span>;
  return (
    <nav aria-label="Breadcrumb" className="flex min-w-0 items-center gap-1.5 text-sm">
      <Link to={nav?.to ?? "/"} className="text-slate-600 hover:text-ink">{nav?.label ?? parts[0]}</Link>
      {parts.slice(1).map((p, i) => (
        <span key={i} className="flex min-w-0 items-center gap-1.5 text-slate-400">/<span className="truncate text-ink">
          {/^\d+$/.test(p) ? `#${p}` : p.replace(/-/g, " ")}</span></span>
      ))}
    </nav>
  );
}

function GlobalSearch() {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [debounced, setDebounced] = useState("");
  const nav = useNavigate();
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => { const t = setTimeout(() => setDebounced(q.trim()), 250); return () => clearTimeout(t); }, [q]);
  useEffect(() => {
    const h = (e: MouseEvent) => { if (box.current && !box.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);
  const res = useQuery({ queryKey: ["search", debounced], enabled: debounced.length >= 2,
    queryFn: () => api.get<{ results: { type: string; id: number; key: string; title: string }[] }>("/search", { q: debounced }) });
  const bases: Record<string, string> = { requirement: "/requirements/", test: "/tests/", defect: "/defects/", execution: "/executions/" };
  const path = (t: string, id: number) => (bases[t] ?? "/") + id;
  return (
    <div ref={box} className="relative w-full max-w-sm">
      <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" aria-hidden />
      <input value={q} onChange={(e) => { setQ(e.target.value); setOpen(true); }} onFocus={() => setOpen(true)}
        placeholder="Search requirements, tests, defects" aria-label="Global search"
        className="h-9 w-full rounded-md border border-slate-300 bg-slate-50 pl-8 pr-2 text-sm focus:border-accent focus:bg-white focus:outline-none focus:ring-2 focus:ring-accent-soft" />
      {open && debounced.length >= 2 && (
        <div className="absolute z-30 mt-1 w-full overflow-hidden rounded-md border border-slate-200 bg-white shadow-lg" role="listbox">
          {res.isLoading ? <p className="px-3 py-2 text-sm text-slate-500">Searching…</p> :
            !res.data?.results.length ? <p className="px-3 py-2 text-sm text-slate-500">No matches for “{debounced}”</p> :
              res.data.results.map((r) => (
                <button key={r.type + r.id} role="option" aria-selected={false}
                  onClick={() => { setOpen(false); setQ(""); nav(path(r.type, r.id)); }}
                  className="flex w-full items-baseline gap-2 px-3 py-2 text-left text-sm hover:bg-slate-50 focus:bg-accent-soft focus:outline-none">
                  <span className="w-20 shrink-0 text-2xs text-slate-500">{r.type}</span>
                  <span className="font-mono text-xs text-slate-600">{r.key}</span>
                  <span className="truncate text-ink">{r.title}</span>
                </button>
              ))}
        </div>
      )}
    </div>
  );
}

function Notifications() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["notifications"], queryFn: () =>
    api.get<{ id: number; title: string; body: string; link: string | null; read: boolean; at: string }[]>("/notifications"),
  refetchInterval: 60_000 });
  const unread = q.data?.filter((n) => !n.read).length ?? 0;
  const nav = useNavigate();
  return (
    <Dropdown.Root>
      <Dropdown.Trigger className="relative rounded-md p-2 text-slate-600 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-ring"
        aria-label={`Notifications${unread ? `, ${unread} unread` : ""}`}>
        <Bell className="h-4 w-4" />
        {unread > 0 && <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-accent" />}
      </Dropdown.Trigger>
      <Dropdown.Portal>
        <Dropdown.Content align="end" sideOffset={6} className="z-40 w-80 rounded-md border border-slate-200 bg-white p-1 shadow-lg">
          {!q.data?.length ? <p className="px-3 py-3 text-sm text-slate-500">No notifications</p> : q.data.map((n) => (
            <Dropdown.Item key={n.id} onSelect={async () => {
              await api.post(`/notifications/${n.id}/read`); qc.invalidateQueries({ queryKey: ["notifications"] });
              if (n.link) nav(n.link);
            }} className="cursor-pointer rounded px-3 py-2 text-sm outline-none data-[highlighted]:bg-slate-50">
              <p className={cn("text-ink", !n.read && "font-medium")}>{n.title}</p>
              <p className="text-xs text-slate-600">{n.body}</p>
              <p className="mt-0.5 text-2xs text-slate-400">{fmtDate(n.at)}</p>
            </Dropdown.Item>
          ))}
        </Dropdown.Content>
      </Dropdown.Portal>
    </Dropdown.Root>
  );
}

export function AppShell() {
  const { me, signOut } = useAuth();
  const { projects, projectId, setProjectId } = useProjects();
  const [collapsed, setCollapsed] = useState(false);
  const nav = useNavigate();
  const cfg = useQuery({ queryKey: ["config"], queryFn: () => api.get<any>("/config"), staleTime: 60_000 });
  const llmReady = cfg.data?.llm?.any_configured;

  return (
    <div className="flex h-[100dvh] min-h-[100dvh] bg-slate-50 text-ink">
      <aside className={cn("flex shrink-0 flex-col border-r border-slate-200 bg-white transition-[width]",
        collapsed ? "w-14" : "w-56")} aria-label="Primary">
        <div className="flex h-14 items-center justify-between border-b border-slate-200 px-3">
          <Link to="/" aria-label="TraceTest AI overview"><Wordmark compact={collapsed} /></Link>
        </div>
        <nav className="flex-1 overflow-y-auto py-2">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end} title={collapsed ? n.label : undefined}
              className={({ isActive }) => cn("mx-2 my-0.5 flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-sm",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-ring",
                isActive ? "bg-accent-soft font-medium text-accent" : "text-slate-700 hover:bg-slate-100")}>
              <n.icon className="h-4 w-4 shrink-0" aria-hidden />{!collapsed && <span className="truncate">{n.label}</span>}
            </NavLink>
          ))}
        </nav>
        <button onClick={() => setCollapsed(!collapsed)} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="flex items-center gap-2 border-t border-slate-200 px-4 py-2.5 text-xs text-slate-500 hover:bg-slate-50">
          {collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <><PanelLeftClose className="h-4 w-4" />Collapse</>}
        </button>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center gap-3 border-b border-slate-200 bg-white px-4">
          <select aria-label="Project" value={projectId ?? ""} onChange={(e) => setProjectId(e.target.value ? Number(e.target.value) : null)}
            className="h-9 max-w-[14rem] rounded-md border border-slate-300 bg-white px-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent-soft">
            <option value="">All projects</option>
            {projects.map((p) => <option key={p.id} value={p.id}>{p.key} — {p.name}</option>)}
          </select>
          <GlobalSearch />
          <div className="ml-auto flex items-center gap-2">
            <span className="hidden items-center gap-1.5 rounded border border-slate-200 px-2 py-1 text-2xs text-slate-600 xl:inline-flex"
              title={llmReady ? "An AI provider is configured" : "No AI provider configured"}>
              <Activity className={cn("h-3 w-3", llmReady ? "text-emerald-600" : "text-amber-600")} aria-hidden />
              {cfg.data?.environment ?? "…"},{" "}
              {llmReady ? `AI ${cfg.data?.llm?.mode === "mock" ? "fixture mode" : "ready"}` : "AI not configured"}
            </span>
            <Notifications />
            <Dropdown.Root>
              <Dropdown.Trigger className="flex items-center gap-2 rounded-md px-2 py-1 text-left hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-ring">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-200 text-xs font-medium text-slate-700" aria-hidden>
                  {me?.user.full_name.split(" ").map((s) => s[0]).join("").slice(0, 2)}</span>
                <span className="hidden whitespace-nowrap text-sm leading-tight lg:block">{me?.user.full_name}
                  <span className="block text-2xs text-slate-500">{me?.roles.map((r) => r.replace("_", " ")).join(", ")}</span></span>
              </Dropdown.Trigger>
              <Dropdown.Portal>
                <Dropdown.Content align="end" sideOffset={6} className="z-40 w-52 rounded-md border border-slate-200 bg-white p-1 shadow-lg">
                  <Dropdown.Item onSelect={() => nav("/settings")} className="cursor-pointer rounded px-3 py-2 text-sm outline-none data-[highlighted]:bg-slate-50">Settings</Dropdown.Item>
                  <Dropdown.Item onSelect={async () => { await signOut(); nav("/login"); }}
                    className="flex cursor-pointer items-center gap-2 rounded px-3 py-2 text-sm outline-none data-[highlighted]:bg-slate-50">
                    <LogOut className="h-3.5 w-3.5" />Sign out</Dropdown.Item>
                </Dropdown.Content>
              </Dropdown.Portal>
            </Dropdown.Root>
          </div>
        </header>
        <div className="flex h-10 shrink-0 items-center border-b border-slate-200 bg-white/60 px-5"><Breadcrumbs /></div>
        <main className="min-w-0 flex-1 overflow-y-auto px-5 py-5" id="main"><Outlet /></main>
      </div>
    </div>
  );
}
