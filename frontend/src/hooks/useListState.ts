import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

export interface ListState {
  page: number; pageSize: number; sort: string; order: "asc" | "desc"; q: string; filters: Record<string, string>;
  setPage: (p: number) => void; setPageSize: (n: number) => void; setSort: (k: string) => void; setQ: (q: string) => void;
  setFilter: (k: string, v: string) => void; clear: () => void; params: Record<string, string | number>;
}

/** Table state persisted in the URL so filters are shareable and survive reloads. */
export function useListState(filterKeys: string[], defaults: { sort?: string; order?: "asc" | "desc" } = {}): ListState {
  const [sp, setSp] = useSearchParams();
  const update = useCallback((fn: (p: URLSearchParams) => void) => {
    setSp((prev) => { const n = new URLSearchParams(prev); fn(n); return n; }, { replace: true });
  }, [setSp]);
  const filters = useMemo(() => Object.fromEntries(filterKeys.map((k) => [k, sp.get(k) ?? ""])),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [sp, filterKeys.join(",")]);
  const page = Number(sp.get("page") ?? 1);
  const pageSize = Number(sp.get("page_size") ?? 25);
  const sort = sp.get("sort") ?? defaults.sort ?? "";
  const order = (sp.get("order") as "asc" | "desc") ?? defaults.order ?? "desc";
  const q = sp.get("q") ?? "";
  const setOrDel = (p: URLSearchParams, k: string, v: string) => (v ? p.set(k, v) : p.delete(k));
  return {
    page, pageSize, sort, order, q, filters,
    setPage: (n) => update((p) => p.set("page", String(n))),
    setPageSize: (n) => update((p) => { p.set("page_size", String(n)); p.set("page", "1"); }),
    setSort: (k) => update((p) => {
      const same = (p.get("sort") ?? defaults.sort) === k;
      p.set("sort", k); p.set("order", same && order === "desc" ? "asc" : "desc"); p.set("page", "1");
    }),
    setQ: (v) => update((p) => { setOrDel(p, "q", v); p.set("page", "1"); }),
    setFilter: (k, v) => update((p) => { setOrDel(p, k, v); p.set("page", "1"); }),
    clear: () => update((p) => { [...filterKeys, "q"].forEach((k) => p.delete(k)); p.set("page", "1"); }),
    params: { page, page_size: pageSize, ...(sort ? { sort, order } : {}), ...(q ? { q } : {}),
      ...Object.fromEntries(Object.entries(filters).filter(([, v]) => v)) },
  };
}
