import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { ToastProvider } from "@/components/Toast";
import { AuthProvider } from "@/hooks/useAuth";
import { ProjectProvider } from "@/hooks/useProjects";

export const ME = {
  user: { id: 3, email: "reviewer@northwind-hcm.example", full_name: "Riley Chen", title: "QA Lead", is_active: true, can_login: true,
    roles: ["reviewer"], last_login_at: null, created_at: "2026-06-01T00:00:00Z" },
  roles: ["reviewer"], permissions: ["project.read", "test.review", "defect.approve"], csrf_token: "x", project_ids: [1],
};

type Route = [RegExp, unknown | ((url: string, init?: RequestInit) => unknown), number?];

export function mockFetch(routes: Route[]) {
  const calls: { url: string; init?: RequestInit }[] = [];
  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    calls.push({ url, init });
    const r = routes.find(([re]) => re.test(url));
    const status = r?.[2] ?? (r ? 200 : 404);
    const body = r ? (typeof r[1] === "function" ? (r[1] as any)(url, init) : r[1]) :
      { error: { code: "not_found", message: "Not found", details: null, trace_id: "t-404" } };
    return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json", "X-Trace-Id": "trace-abc" } });
  }) as typeof fetch;
  return calls;
}

export function renderApp(ui: ReactNode, { route = "/", withProjects = true } = {}) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[route]}>
        <ToastProvider><AuthProvider>{withProjects ? <ProjectProvider>{ui}</ProjectProvider> : ui}</AuthProvider></ToastProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

export const page = <T,>(items: T[], total = items.length) => ({ items, total, page: 1, page_size: 25 });
