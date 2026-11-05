import { useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { z } from "zod";
import { Button, Field, Input, Notice } from "@/components/ui";
import { useAuth } from "@/hooks/useAuth";
import { Wordmark } from "@/layouts/AppShell";
import { api, ApiError } from "@/services/api";

const schema = z.object({ email: z.string().email("Enter a valid email address"), password: z.string().min(1, "Enter your password") });

export default function LoginPage() {
  const { me } = useAuth();
  const qc = useQueryClient();
  const nav = useNavigate();
  const [form, setForm] = useState({ email: "", password: "" });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [failure, setFailure] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  if (me) return <Navigate to="/" replace />;

  async function submit(e: FormEvent) {
    e.preventDefault();
    const parsed = schema.safeParse(form);
    if (!parsed.success) { setErrors(Object.fromEntries(parsed.error.issues.map((i) => [String(i.path[0]), i.message]))); return; }
    setErrors({}); setFailure(null); setBusy(true);
    try {
      await api.post("/auth/login", parsed.data);
      await qc.invalidateQueries({ queryKey: ["me"] });
      nav("/");
    } catch (err) {
      setFailure(err instanceof ApiError ? err.message : "Sign-in failed. Check that the API is running.");
    } finally { setBusy(false); }
  }

  return (
    <div className="flex min-h-[100dvh] bg-slate-50">
      <div className="hidden w-[44%] flex-col justify-between border-r border-slate-200 bg-white p-10 lg:flex">
        <Wordmark />
        <div className="max-w-md">
          <p className="text-2xl font-semibold leading-snug tracking-tight text-ink">
            Every requirement clause, traced to the tests that prove it and the defects that break it.</p>
          <p className="mt-3 text-sm leading-relaxed text-slate-600">TraceTest AI turns business requirements into reviewed,
            executable tests, runs them against your system under test and keeps the evidence linked end to end.</p>
        </div>
        <p className="text-xs text-slate-500">Sign-in is limited to provisioned accounts. Contact your workspace administrator for access.</p>
      </div>
      <div className="flex flex-1 items-center justify-center p-6">
        <form onSubmit={submit} className="w-full max-w-sm space-y-4" noValidate>
          <div className="lg:hidden"><Wordmark /></div>
          <div>
            <h1 className="text-xl font-semibold text-ink">Sign in</h1>
            <p className="text-sm text-slate-600">Dayforce Quality Engineering Workspace</p>
          </div>
          <div className="rounded-md border border-accent/20 bg-accent-soft p-3 text-xs text-accent">
            <span className="font-semibold">Local Development:</span> When accessing on localhost, you are automatically signed in as Dayforce QA Engineer. If you are redirected here or need to switch roles, use your provisioned credentials.
          </div>
          {failure && <Notice tone="danger">{failure}</Notice>}
          <Field label="Work email" htmlFor="email" error={errors.email}>
            <Input id="email" type="email" autoComplete="username" value={form.email}
              placeholder="e.g. qa.engineer@dayforce-qa.local"
              onChange={(e) => setForm({ ...form, email: e.target.value })} aria-invalid={!!errors.email} />
          </Field>
          <Field label="Password" htmlFor="password" error={errors.password}>
            <Input id="password" type="password" autoComplete="current-password" value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })} aria-invalid={!!errors.password} />
          </Field>
          <Button type="submit" variant="primary" className="w-full" loading={busy}>Sign in</Button>
          <p className="text-center text-2xs text-slate-400">
            Independent Quality Engineering Prototype &bull; Not officially affiliated with Dayforce Inc.
          </p>
        </form>
      </div>
    </div>
  );
}
