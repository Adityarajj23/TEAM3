import type { components } from "@/types/api.gen";

export type Schemas = components["schemas"];

export class ApiError extends Error {
  status: number;
  code: string;
  details: unknown;
  traceId: string | null;
  constructor(status: number, code: string, message: string, details: unknown, traceId: string | null) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
    this.traceId = traceId;
  }
}

function csrfToken(): string {
  const m = document.cookie.match(/(?:^|; )tt_csrf=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : "";
}

type Query = Record<string, string | number | boolean | null | undefined>;

export function qs(params: Query = {}): string {
  const p = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") p.set(k, String(v));
  });
  const s = p.toString();
  return s ? `?${s}` : "";
}

async function request<T>(method: string, path: string, body?: unknown, isForm = false): Promise<T> {
  const headers: Record<string, string> = {};
  if (method !== "GET") headers["X-CSRF-Token"] = csrfToken();
  if (body !== undefined && !isForm) headers["Content-Type"] = "application/json";
  const res = await fetch(`/api/v1${path}`, {
    method,
    credentials: "include",
    headers,
    body: body === undefined ? undefined : isForm ? (body as FormData) : JSON.stringify(body),
  });
  if (!res.ok) {
    let payload: any = null;
    try {
      payload = await res.json();
    } catch {
      /* non-JSON error */
    }
    const e = payload?.error;
    throw new ApiError(res.status, e?.code ?? "http_error", e?.message ?? res.statusText, e?.details,
      e?.trace_id ?? res.headers.get("X-Trace-Id"));
  }
  const ct = res.headers.get("content-type") ?? "";
  return (ct.includes("application/json") ? res.json() : res.text()) as Promise<T>;
}

export const api = {
  get: <T>(path: string, params?: Query) => request<T>("GET", path + qs(params)),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body ?? {}),
  patch: <T>(path: string, body: unknown) => request<T>("PATCH", path, body),
  put: <T>(path: string, body: unknown) => request<T>("PUT", path, body),
  delete: <T>(path: string) => request<T>("DELETE", path),
  upload: <T>(path: string, form: FormData) => request<T>("POST", path, form, true),
};

export function downloadUrl(path: string, params?: Query) {
  return `/api/v1${path}${qs(params)}`;
}
