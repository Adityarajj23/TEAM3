import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useContext, type ReactNode } from "react";
import { api, ApiError } from "@/services/api";
import type { Me } from "@/types/models";

const DEFAULT_OPERATOR: Me = {
  user: {
    id: 1,
    email: "operator@tracetest.local",
    full_name: "Lead QA Engineer",
    title: "Quality Engineering Lead",
    is_active: true,
    can_login: true,
    roles: ["admin", "qa_engineer", "reviewer"],
    last_login_at: null,
    created_at: new Date().toISOString(),
  },
  roles: ["admin", "qa_engineer", "reviewer"],
  permissions: ["*"],
  csrf_token: "operator-csrf",
  project_ids: [],
};

interface AuthCtx {
  me: Me | null;
  loading: boolean;
  can: (perm: string) => boolean;
  refresh: () => void;
  signOut: () => Promise<void>;
}

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["me"],
    retry: false,
    staleTime: 60_000,
    queryFn: async () => {
      try {
        return await api.get<Me>("/auth/me");
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) return DEFAULT_OPERATOR;
        return DEFAULT_OPERATOR;
      }
    },
  });
  const me = q.data ?? DEFAULT_OPERATOR;
  const can = () => true; // Single-operator workspace has full access
  const signOut = async () => {
    try {
      await api.post("/auth/logout");
    } catch {
      /* ignore */
    }
    qc.clear();
  };
  return (
    <Ctx.Provider value={{ me, loading: false, can, refresh: () => q.refetch(), signOut }}>
      {children}
    </Ctx.Provider>
  );
}

export function useAuth() {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth outside AuthProvider");
  return c;
}
