import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export const cn = (...v: ClassValue[]) => twMerge(clsx(v));

export function fmtDate(iso?: string | null, withTime = true): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString(undefined, withTime
    ? { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }
    : { year: "numeric", month: "short", day: "numeric" });
}

export function fmtDuration(ms?: number | null): string {
  if (ms === null || ms === undefined) return "—";
  if (ms < 1) return "<1 ms";
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}

export const pct = (v: number | null | undefined) => (v === null || v === undefined ? "—" : `${v.toFixed(1)}%`);

export function label(s?: string | null): string {
  if (!s) return "—";
  const t = s.replace(/_/g, " ");
  return t.charAt(0).toUpperCase() + t.slice(1);
}
