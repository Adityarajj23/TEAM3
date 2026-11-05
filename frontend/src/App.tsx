import { useEffect } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { LoadingBlock } from "@/components/ui";
import { useAuth } from "@/hooks/useAuth";
import { ProjectProvider } from "@/hooks/useProjects";
import { AppShell } from "@/layouts/AppShell";
import DashboardPage from "@/pages/DashboardPage";
import { DefectDetailPage, DefectsPage, ExecutionDetailPage, ExecutionsPage } from "@/pages/ExecutionDefectPages";
import { AnalyticsPage, AuditPage, EvaluationsPage, IntegrationsPage, SettingsPage, TraceabilityPage } from "@/pages/InsightPages";
import LoginPage from "@/pages/LoginPage";
import { ProjectDetailPage, ProjectsPage } from "@/pages/ProjectsPage";
import { RequirementDetailPage, RequirementsPage } from "@/pages/RequirementsPages";
import { ReviewWorkspacePage, SuiteDetailPage, SuitesPage, TestDetailPage, TestsPage } from "@/pages/TestPages";

const TITLES: [RegExp, string][] = [[/^\/$/, "Overview"], [/^\/projects/, "Projects"], [/^\/requirements/, "Requirements"],
  [/^\/tests\/review/, "Approval workspace"], [/^\/tests/, "Test cases"], [/^\/suites/, "Test suites"], [/^\/executions/, "Test executions"],
  [/^\/defects/, "Defects"], [/^\/traceability/, "Traceability"], [/^\/analytics/, "Quality analytics"], [/^\/evaluations/, "AI evaluations"],
  [/^\/audit/, "Audit logs"], [/^\/integrations/, "Integrations"], [/^\/settings/, "Settings"], [/^\/login/, "Sign in"]];

function useTitle() {
  const { pathname } = useLocation();
  useEffect(() => {
    const t = TITLES.find(([r]) => r.test(pathname))?.[1];
    document.title = t ? `${t} | TraceTest AI` : "TraceTest AI";
  }, [pathname]);
}

function Protected() {
  const { me, loading } = useAuth();
  const loc = useLocation();
  if (loading) return <div className="p-8"><LoadingBlock rows={6} /></div>;
  if (!me) return <Navigate to="/login" replace state={{ from: loc.pathname }} />;
  return <ProjectProvider><AppShell /></ProjectProvider>;
}

export default function App() {
  useTitle();
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<Protected />}>
        <Route index element={<DashboardPage />} />
        <Route path="projects" element={<ProjectsPage />} />
        <Route path="projects/:id" element={<ProjectDetailPage />} />
        <Route path="requirements" element={<RequirementsPage />} />
        <Route path="requirements/:id" element={<RequirementDetailPage />} />
        <Route path="tests" element={<TestsPage />} />
        <Route path="tests/review" element={<ReviewWorkspacePage />} />
        <Route path="tests/:id" element={<TestDetailPage />} />
        <Route path="suites" element={<SuitesPage />} />
        <Route path="suites/:id" element={<SuiteDetailPage />} />
        <Route path="executions" element={<ExecutionsPage />} />
        <Route path="executions/:id" element={<ExecutionDetailPage />} />
        <Route path="defects" element={<DefectsPage />} />
        <Route path="defects/:id" element={<DefectDetailPage />} />
        <Route path="traceability" element={<TraceabilityPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="evaluations" element={<EvaluationsPage />} />
        <Route path="audit" element={<AuditPage />} />
        <Route path="integrations" element={<IntegrationsPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<div className="py-16 text-center"><p className="text-lg font-semibold">Page not found</p>
          <p className="text-sm text-slate-600">The address may be mistyped, or the record may have been removed.</p></div>} />
      </Route>
    </Routes>
  );
}
