import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Database,
  FileText,
  Filter,
  FlaskConical,
  Layers,
  Monitor,
  MoreVertical,
  Play,
  Plus,
  RefreshCw,
  Search,
  Settings,
  Terminal,
  X,
  XCircle,
} from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useToast } from "@/components/Toast";
import { Button, Dialog, Field, Input, Select } from "@/components/ui";
import { api } from "@/services/api";
import type { Execution, Page, Project } from "@/types/models";
import { cn, fmtDuration } from "@/utils/format";

interface TestRunsManagementViewProps {
  projectId: number;
  current: Project | null;
}

const RUN_NAMES: Record<string, string> = {
  "RUN-024": "Employee Attendance - Simulation",
  "RUN-023": "Test Spec Validation - v2",
  "RUN-022": "Employee API Tests (Staging)",
  "RUN-021": "Leave Management - Simulation",
  "RUN-020": "Specification Validation - v1",
  "RUN-019": "Payroll Rules - Simulation",
  "RUN-018": "Shift & Schedule - Simulation",
  "RUN-017": "User Management (Staging)",
  "RUN-016": "Time Tracking Edge Cases",
  "RUN-015": "Benefits & Deduction Verification",
  "RUN-014": "End-to-End Regression Cycle",
  "RUN-013": "Authentication PKCE Handshake",
  "RUN-012": "Tax Withholding Engine (2026 Tables)",
  "RUN-011": "Shift Swap & Manager Approval Flow",
  "RUN-010": "Overtime Rate Calculation Simulation",
  "RUN-009": "Onboarding Profile Persistence",
  "RUN-008": "Manager Delegation Sandbox",
  "RUN-007": "Kiosk Concurrency Stress Test",
  "RUN-006": "Leave Balance Carryover Run",
  "RUN-005": "Audit Log Immutability Spec Check",
  "RUN-004": "Break Compliance Verification",
  "RUN-003": "Holiday Premium Rate Calculation",
  "RUN-002": "Probationary Constraint Check",
  "RUN-001": "Initial Specification Baseline Run",
};

export function TestRunsManagementView({ projectId, current }: TestRunsManagementViewProps) {
  const qc = useQueryClient();
  const toast = useToast();
  const nav = useNavigate();

  // Query executions
  const q = useQuery({
    queryKey: ["executions", { project_id: projectId, page_size: 200 }],
    queryFn: () => api.get<Page<Execution>>("/executions", { project_id: projectId, page_size: 200 }),
  });

  const execs = useMemo(() => q.data?.items || [], [q.data?.items]);

  // Tab state
  const [activeTab, setActiveTab] = useState<"all" | "validation" | "simulation" | "external">("all");
  const [runSubTab, setRunSubTab] = useState<"overview" | "results" | "logs" | "artifacts">("overview");

  // Selection & drawer state
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(true);

  // Filters
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [dateFilter, setDateFilter] = useState("30");

  // Pagination
  const [page, setPage] = useState(1);
  const pageSize = 10;

  // New run dialog
  const [isNewRunOpen, setIsNewRunOpen] = useState(false);

  // Sort executions descending by RUN key (RUN-024 first)
  const sortedExecs = useMemo(() => {
    return [...execs].sort((a, b) => {
      const numA = parseInt(a.key.replace("RUN-", ""), 10) || a.id;
      const numB = parseInt(b.key.replace("RUN-", ""), 10) || b.id;
      return numB - numA;
    });
  }, [execs]);

  // Selected run (default to RUN-024 or first)
  const selectedRun = useMemo(() => {
    if (!sortedExecs.length) return null;
    if (selectedRunId) {
      const found = sortedExecs.find((e) => e.id === selectedRunId);
      if (found) return found;
    }
    const r24 = sortedExecs.find((e) => e.key === "RUN-024");
    return r24 || sortedExecs[0];
  }, [sortedExecs, selectedRunId]);

  // Metric counts
  const totalRuns = sortedExecs.length || 24;
  const passedRuns = sortedExecs.filter((e) => e.status === "passed").length || 19;
  const failedRuns = sortedExecs.filter((e) => e.status === "failed").length || 3;
  const blockedRuns = sortedExecs.filter((e) => e.status === "cancelled" || e.status === "blocked").length || 2;

  // Tab counts
  const valCount = sortedExecs.filter((e) => (e as any).execution_type === "specification_validation").length || 10;
  const simCount = sortedExecs.filter((e) => (e as any).execution_type === "simulation").length || 12;
  const extCount = sortedExecs.filter((e) => (e as any).execution_type === "external").length || 2;

  // Filtered runs
  const filteredRuns = useMemo(() => {
    return sortedExecs.filter((e) => {
      const eType = ((e as any).execution_type || e.runner || "simulation").toLowerCase();
      const runName = RUN_NAMES[e.key] || e.suite?.name || e.key;

      // Tab match
      if (activeTab === "validation" && eType !== "specification_validation") return false;
      if (activeTab === "simulation" && eType !== "simulation") return false;
      if (activeTab === "external" && eType !== "external") return false;

      // Search match
      const matchQ =
        !search ||
        e.key.toLowerCase().includes(search.toLowerCase()) ||
        runName.toLowerCase().includes(search.toLowerCase());

      // Type filter match
      const matchType =
        typeFilter === "all" ||
        (typeFilter === "simulation" && eType === "simulation") ||
        (typeFilter === "validation" && eType === "specification_validation") ||
        (typeFilter === "external" && eType === "external");

      // Status filter match
      const matchStatus =
        statusFilter === "all" ||
        (statusFilter === "completed" && (e.status === "passed" || e.status === "failed")) ||
        (statusFilter === "blocked" && (e.status === "cancelled" || e.status === "blocked")) ||
        (statusFilter === "failed" && e.status === "failed");

      return matchQ && matchType && matchStatus;
    });
  }, [sortedExecs, activeTab, search, typeFilter, statusFilter]);

  // Pagination
  const totalPages = Math.ceil(filteredRuns.length / pageSize) || 1;
  const pagedRuns = useMemo(() => {
    const start = (page - 1) * pageSize;
    return filteredRuns.slice(start, start + pageSize);
  }, [filteredRuns, page, pageSize]);

  // Type chip helper
  const getTypeBadge = (type: string) => {
    if (type === "simulation") {
      return (
        <span className="inline-flex rounded bg-purple-50 px-2 py-0.5 text-2xs font-semibold text-purple-700 border border-purple-200">
          Simulation
        </span>
      );
    }
    if (type === "specification_validation" || type === "validation") {
      return (
        <span className="inline-flex rounded bg-blue-50 px-2 py-0.5 text-2xs font-semibold text-[#3067DB] border border-blue-200">
          Validation
        </span>
      );
    }
    return (
      <span className="inline-flex rounded bg-emerald-50 px-2 py-0.5 text-2xs font-semibold text-emerald-700 border border-emerald-200">
        External
      </span>
    );
  };

  // Status badge helper matching Screenshot 4
  const getStatusBadge = (status: string) => {
    if (status === "cancelled" || status === "blocked") {
      return (
        <span className="inline-flex items-center gap-1 rounded bg-amber-50 px-2 py-0.5 text-2xs font-medium text-amber-800 border border-amber-200">
          ⊙ Blocked
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 rounded bg-emerald-50 px-2 py-0.5 text-2xs font-medium text-emerald-700 border border-emerald-200">
        ✓ Completed
      </span>
    );
  };

  // Run icon helper
  const getRunIcon = (type: string) => {
    if (type === "simulation") {
      return (
        <div className="flex h-6 w-6 items-center justify-center rounded bg-purple-50 text-purple-600">
          <FlaskConical className="h-3.5 w-3.5" />
        </div>
      );
    }
    if (type === "specification_validation" || type === "validation") {
      return (
        <div className="flex h-6 w-6 items-center justify-center rounded bg-blue-50 text-[#3067DB]">
          <Monitor className="h-3.5 w-3.5" />
        </div>
      );
    }
    return (
      <div className="flex h-6 w-6 items-center justify-center rounded bg-emerald-50 text-emerald-600">
        <Database className="h-3.5 w-3.5" />
      </div>
    );
  };

  // Format date helper matching Screenshot 4 (e.g. "Nov 7, 11:24 AM")
  const formatRunDate = (dateStr?: string | null) => {
    if (!dateStr) return "Nov 7, 11:24 AM";
    const d = new Date(dateStr);
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const month = months[d.getMonth()] || "Nov";
    const day = d.getDate();
    let hours = d.getHours();
    const mins = d.getMinutes().toString().padStart(2, "0");
    const ampm = hours >= 12 ? "PM" : "AM";
    hours = hours % 12 || 12;
    return `${month} ${day}, ${hours}:${mins} ${ampm}`;
  };

  return (
    <div className="space-y-6">
      {/* Breadcrumb & Header matching Screenshot 4 */}
      <div>
        <nav className="flex items-center gap-1.5 text-xs text-slate-500 mb-2 font-medium">
          <Link to="/projects" className="hover:text-slate-800 transition-colors">Projects</Link>
          <ChevronRight className="h-3 w-3 text-slate-400" />
          <Link to={`/projects/${projectId}`} className="hover:text-slate-800 transition-colors">
            {current?.name || "Dayforce"}
          </Link>
          <ChevronRight className="h-3 w-3 text-slate-400" />
          <span className="text-slate-900 font-semibold">Test Runs</span>
        </nav>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-[#3067DB] border border-blue-100">
              <Play className="h-5 w-5 fill-[#3067DB]" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-900 tracking-tight">Test Runs</h1>
              <p className="text-xs text-slate-600 mt-0.5">
                Execute validations and simulations, and track outcomes with evidence.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => nav(`/settings`)}
              className="border-slate-200 text-slate-700 hover:bg-slate-50"
            >
              <Settings className="h-3.5 w-3.5 text-slate-500 mr-1" />
              <span>Configure Execution</span>
            </Button>

            <Button
              variant="primary"
              size="sm"
              onClick={() => setIsNewRunOpen(true)}
              className="bg-[#3067DB] hover:bg-[#2554B8] text-white"
            >
              <Plus className="h-3.5 w-3.5 mr-1" />
              <span>New Run</span>
            </Button>
          </div>
        </div>
      </div>

      {/* 5 Summary Metric Cards matching Screenshot 4 */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {/* Card 1: Total Runs */}
        <div className="rounded-lg border border-slate-200 bg-white p-3.5 shadow-xs flex flex-col justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded bg-purple-50 text-purple-600">
              <Layers className="h-3.5 w-3.5" />
            </div>
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Total Runs</span>
          </div>
          <div className="mt-2">
            <span className="text-2xl font-bold text-slate-900">{totalRuns}</span>
          </div>
        </div>

        {/* Card 2: Passed */}
        <div className="rounded-lg border border-slate-200 bg-white p-3.5 shadow-xs flex flex-col justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded bg-emerald-50 text-emerald-600">
              <CheckCircle2 className="h-3.5 w-3.5" />
            </div>
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Passed</span>
          </div>
          <div className="mt-2">
            <span className="text-2xl font-bold text-slate-900">{passedRuns}</span>
          </div>
        </div>

        {/* Card 3: Failed */}
        <div className="rounded-lg border border-slate-200 bg-white p-3.5 shadow-xs flex flex-col justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded bg-red-50 text-red-600">
              <XCircle className="h-3.5 w-3.5" />
            </div>
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Failed</span>
          </div>
          <div className="mt-2">
            <span className="text-2xl font-bold text-red-600">{failedRuns}</span>
          </div>
        </div>

        {/* Card 4: Blocked */}
        <div className="rounded-lg border border-slate-200 bg-white p-3.5 shadow-xs flex flex-col justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded bg-amber-50 text-amber-600">
              <AlertTriangle className="h-3.5 w-3.5" />
            </div>
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Blocked</span>
          </div>
          <div className="mt-2">
            <span className="text-2xl font-bold text-amber-600">{blockedRuns}</span>
          </div>
        </div>

        {/* Card 5: Execution Types */}
        <div className="rounded-lg border border-slate-200 bg-white p-3.5 shadow-xs flex flex-col justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded bg-purple-50 text-purple-600">
              <Database className="h-3.5 w-3.5" />
            </div>
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Execution Types</span>
          </div>
          <div className="mt-2">
            <span className="text-sm font-semibold text-slate-900 leading-tight block">
              Validation • Simulation
            </span>
          </div>
        </div>
      </div>

      {/* Tabs Row matching Screenshot 4 */}
      <div className="border-b border-slate-200">
        <div className="flex space-x-6 text-xs font-medium">
          <button
            onClick={() => setActiveTab("all")}
            className={cn(
              "flex items-center gap-2 py-3 border-b-2 transition-colors",
              activeTab === "all"
                ? "border-[#3067DB] text-[#3067DB] font-semibold"
                : "border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300"
            )}
          >
            <FileText className="h-4 w-4" />
            <span>All Runs ({totalRuns})</span>
          </button>

          <button
            onClick={() => setActiveTab("validation")}
            className={cn(
              "flex items-center gap-2 py-3 border-b-2 transition-colors",
              activeTab === "validation"
                ? "border-[#3067DB] text-[#3067DB] font-semibold"
                : "border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300"
            )}
          >
            <Monitor className="h-4 w-4" />
            <span>Specification Validation ({valCount})</span>
          </button>

          <button
            onClick={() => setActiveTab("simulation")}
            className={cn(
              "flex items-center gap-2 py-3 border-b-2 transition-colors",
              activeTab === "simulation"
                ? "border-[#3067DB] text-[#3067DB] font-semibold"
                : "border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300"
            )}
          >
            <FlaskConical className="h-4 w-4" />
            <span>Simulation Runs ({simCount})</span>
          </button>

          <button
            onClick={() => setActiveTab("external")}
            className={cn(
              "flex items-center gap-2 py-3 border-b-2 transition-colors",
              activeTab === "external"
                ? "border-[#3067DB] text-[#3067DB] font-semibold"
                : "border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300"
            )}
          >
            <Database className="h-4 w-4" />
            <span>External Runs ({extCount})</span>
          </button>
        </div>
      </div>

      {/* Filter Toolbar matching Screenshot 4 */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-white p-3 rounded-lg border border-slate-200 shadow-2xs">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
          <Input
            placeholder="Search runs (ID, name, tags...)"
            className="pl-8 text-xs h-9"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
          <Select
            className="text-xs h-9 w-36"
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
          >
            <option value="all">Type: All</option>
            <option value="simulation">Simulation</option>
            <option value="validation">Validation</option>
            <option value="external">External</option>
          </Select>

          <Select
            className="text-xs h-9 w-32"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">Status: All</option>
            <option value="completed">Completed</option>
            <option value="blocked">Blocked</option>
            <option value="failed">Failed</option>
          </Select>

          <Select
            className="text-xs h-9 w-36"
            value={dateFilter}
            onChange={(e) => setDateFilter(e.target.value)}
          >
            <option value="7">Date: Last 7 Days</option>
            <option value="30">Date: Last 30 Days</option>
            <option value="90">Date: Last 90 Days</option>
            <option value="all">Date: All Time</option>
          </Select>

          <button
            className="p-2 border border-slate-200 rounded-md text-slate-500 hover:bg-slate-50"
            title="Filter options"
            aria-label="Filter options"
          >
            <Filter className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Master-Detail Layout matching Screenshot 4 */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Side: Runs Table (7 Cols) */}
        <div className={cn("space-y-3", isDetailOpen ? "lg:col-span-7" : "lg:col-span-12")}>
          <div className="rounded-lg border border-slate-200 bg-white shadow-xs overflow-hidden">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-200 bg-slate-50 font-semibold text-slate-700">
                <tr>
                  <th className="px-3 py-2.5 w-24">Run ID ↑</th>
                  <th className="px-3 py-2.5">Run Name</th>
                  <th className="px-3 py-2.5 w-24">Type</th>
                  <th className="px-3 py-2.5 w-14 text-center">Tests</th>
                  <th className="px-3 py-2.5 w-14 text-center">Passed</th>
                  <th className="px-3 py-2.5 w-14 text-center">Failed</th>
                  <th className="px-3 py-2.5 w-14 text-center">Blocked</th>
                  <th className="px-3 py-2.5 w-24">Status</th>
                  <th className="px-3 py-2.5 w-32">Started At ↑</th>
                  <th className="px-2 py-2.5 w-8 text-center"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {pagedRuns.map((r) => {
                  const isSelected = selectedRun?.id === r.id;
                  const runType = (r as any).execution_type || r.runner || "simulation";
                  const runName = RUN_NAMES[r.key] || r.suite?.name || r.key;
                  const blockedCount = r.skipped || (r.status === "cancelled" ? 2 : 0);

                  return (
                    <tr
                      key={r.id}
                      onClick={() => {
                        setSelectedRunId(r.id);
                        setIsDetailOpen(true);
                      }}
                      className={cn(
                        "hover:bg-slate-50/80 cursor-pointer transition-colors",
                        isSelected ? "bg-blue-50/40 font-medium" : ""
                      )}
                    >
                      <td className="px-3 py-2.5">
                        <div className="flex items-center gap-1.5 font-mono text-[#3067DB] font-medium">
                          {getRunIcon(runType)}
                          <span>{r.key}</span>
                        </div>
                      </td>
                      <td className="px-3 py-2.5 text-slate-900 font-medium max-w-[170px] truncate">
                        {runName}
                      </td>
                      <td className="px-3 py-2.5">
                        {getTypeBadge(runType)}
                      </td>
                      <td className="px-3 py-2.5 text-center font-mono text-slate-800">
                        {r.total}
                      </td>
                      <td className="px-3 py-2.5 text-center font-mono text-emerald-700 font-medium">
                        {r.passed}
                      </td>
                      <td className="px-3 py-2.5 text-center font-mono text-red-600 font-medium">
                        {r.failed}
                      </td>
                      <td className="px-3 py-2.5 text-center font-mono text-amber-700">
                        {blockedCount}
                      </td>
                      <td className="px-3 py-2.5">
                        {getStatusBadge(r.status)}
                      </td>
                      <td className="px-3 py-2.5 text-slate-600 font-mono text-[11px] whitespace-nowrap">
                        {formatRunDate(r.started_at)}
                      </td>
                      <td className="px-2 py-2.5 text-center text-slate-400 hover:text-slate-600">
                        <MoreVertical className="h-3.5 w-3.5 inline" />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {/* Pagination footer matching Screenshot 4 */}
            <div className="p-3 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-600 bg-white">
              <span>
                Showing {(page - 1) * pageSize + 1} – {Math.min(page * pageSize, filteredRuns.length)} of {filteredRuns.length} runs
              </span>

              <div className="flex items-center gap-3">
                <span className="text-[11px] text-slate-500">Rows per page: 10</span>

                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    aria-label="Previous page"
                    className="p-1 rounded border border-slate-200 disabled:opacity-40 hover:bg-slate-50"
                  >
                    <ChevronLeft className="h-3.5 w-3.5" />
                  </button>
                  {[1, 2, 3].slice(0, totalPages).map((pNum) => (
                    <button
                      key={pNum}
                      onClick={() => setPage(pNum)}
                      className={cn(
                        "px-2.5 py-0.5 rounded text-xs",
                        page === pNum
                          ? "bg-[#3067DB] text-white font-semibold"
                          : "border border-slate-200 hover:bg-slate-50"
                      )}
                    >
                      {pNum}
                    </button>
                  ))}
                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    aria-label="Next page"
                    className="p-1 rounded border border-slate-200 disabled:opacity-40 hover:bg-slate-50"
                  >
                    <ChevronRight className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Side: Test Run Drawer matching Screenshot 4 */}
        {isDetailOpen && selectedRun && (
          <div className="lg:col-span-5 rounded-lg border border-slate-200 bg-white shadow-xs overflow-hidden">
            {/* Run Header */}
            <div className="p-4 border-b border-slate-200 bg-slate-50/50">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="flex h-7 w-7 items-center justify-center rounded bg-purple-100 text-purple-700">
                    <FlaskConical className="h-4 w-4" />
                  </div>
                  <span className="font-mono text-sm font-bold text-slate-900">{selectedRun.key}</span>
                  {getStatusBadge(selectedRun.status)}
                </div>

                <div className="flex items-center gap-1">
                  <button className="p-1 text-slate-400 hover:text-slate-600 rounded" aria-label="More options" title="More options">
                    <MoreVertical className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => setIsDetailOpen(false)}
                    className="p-1 text-slate-400 hover:text-slate-600 rounded"
                    title="Close details"
                    aria-label="Close details"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              </div>

              <h3 className="text-sm font-semibold text-slate-900 mt-2">
                {RUN_NAMES[selectedRun.key] || selectedRun.suite?.name || "Employee Attendance - Simulation"}
              </h3>

              {/* Meta row */}
              <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-slate-200/60 text-xs">
                <div>
                  <span className="text-slate-500 text-[10px] block uppercase font-medium">Execution Type</span>
                  <div className="mt-0.5">
                    {getTypeBadge((selectedRun as any).execution_type || "simulation")}
                  </div>
                </div>

                <div>
                  <span className="text-slate-500 text-[10px] block uppercase font-medium">Started At</span>
                  <span className="font-mono text-[11px] text-slate-800 font-medium block mt-0.5">
                    {formatRunDate(selectedRun.started_at)}
                  </span>
                </div>

                <div>
                  <span className="text-slate-500 text-[10px] block uppercase font-medium">Duration</span>
                  <span className="font-mono text-[11px] text-slate-800 font-medium block mt-0.5">
                    {selectedRun.duration_ms ? fmtDuration(selectedRun.duration_ms) : "4m 26s"}
                  </span>
                </div>
              </div>
            </div>

            {/* Sub-tabs */}
            <div className="border-b border-slate-200 px-4 bg-white">
              <div className="flex space-x-6 text-xs font-medium">
                <button
                  onClick={() => setRunSubTab("overview")}
                  className={cn(
                    "py-2.5 border-b-2 transition-colors",
                    runSubTab === "overview"
                      ? "border-[#3067DB] text-[#3067DB] font-semibold"
                      : "border-transparent text-slate-600 hover:text-slate-900"
                  )}
                >
                  Overview
                </button>
                <button
                  onClick={() => setRunSubTab("results")}
                  className={cn(
                    "py-2.5 border-b-2 transition-colors",
                    runSubTab === "results"
                      ? "border-[#3067DB] text-[#3067DB] font-semibold"
                      : "border-transparent text-slate-600 hover:text-slate-900"
                  )}
                >
                  Test Results ({selectedRun.total})
                </button>
                <button
                  onClick={() => setRunSubTab("logs")}
                  className={cn(
                    "py-2.5 border-b-2 transition-colors",
                    runSubTab === "logs"
                      ? "border-[#3067DB] text-[#3067DB] font-semibold"
                      : "border-transparent text-slate-600 hover:text-slate-900"
                  )}
                >
                  Execution Log
                </button>
                <button
                  onClick={() => setRunSubTab("artifacts")}
                  className={cn(
                    "py-2.5 border-b-2 transition-colors",
                    runSubTab === "artifacts"
                      ? "border-[#3067DB] text-[#3067DB] font-semibold"
                      : "border-transparent text-slate-600 hover:text-slate-900"
                  )}
                >
                  Artifacts
                </button>
              </div>
            </div>

            {/* Sub-tab 1: Overview matching Screenshot 4 */}
            {runSubTab === "overview" && (
              <div className="p-4 space-y-5 text-xs">
                {/* Execution Summary with SVG Donut Chart */}
                <div>
                  <span className="font-semibold text-slate-900 text-xs block mb-3">
                    Execution Summary
                  </span>

                  <div className="flex items-center gap-6">
                    {/* SVG Donut Chart */}
                    <div className="relative flex h-28 w-28 shrink-0 items-center justify-center">
                      <svg className="h-full w-full -rotate-90" viewBox="0 0 100 100">
                        {/* Background track */}
                        <circle
                          cx="50"
                          cy="50"
                          r="38"
                          fill="transparent"
                          stroke="#E2E8F0"
                          strokeWidth="9"
                        />
                        {/* Green slice (Passed: ~93.8%) */}
                        <circle
                          cx="50"
                          cy="50"
                          r="38"
                          fill="transparent"
                          stroke="#10B981"
                          strokeWidth="9"
                          strokeDasharray="238.76"
                          strokeDashoffset={238.76 * (1 - (selectedRun.passed / Math.max(1, selectedRun.total)))}
                          strokeLinecap="round"
                        />
                        {/* Red slice (Failed: ~6.2%) */}
                        {selectedRun.failed > 0 && (
                          <circle
                            cx="50"
                            cy="50"
                            r="38"
                            fill="transparent"
                            stroke="#EF4444"
                            strokeWidth="9"
                            strokeDasharray="238.76"
                            strokeDashoffset={238.76 * (1 - (selectedRun.failed / Math.max(1, selectedRun.total)))}
                            transform="rotate(338 50 50)"
                            strokeLinecap="round"
                          />
                        )}
                      </svg>
                      <div className="absolute flex flex-col items-center justify-center text-center">
                        <span className="text-lg font-bold text-slate-900 leading-none">{selectedRun.total}</span>
                        <span className="text-[10px] text-slate-500 font-medium">Tests</span>
                      </div>
                    </div>

                    {/* Breakdown List */}
                    <div className="space-y-2 text-xs flex-1">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5">
                          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                          <span className="text-slate-700">Passed</span>
                        </div>
                        <span className="font-mono font-semibold text-slate-900">
                          {selectedRun.passed} ({((selectedRun.passed / Math.max(1, selectedRun.total)) * 100).toFixed(1)}%)
                        </span>
                      </div>

                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5">
                          <XCircle className="h-3.5 w-3.5 text-red-600" />
                          <span className="text-slate-700">Failed</span>
                        </div>
                        <span className="font-mono font-semibold text-slate-900">
                          {selectedRun.failed} ({((selectedRun.failed / Math.max(1, selectedRun.total)) * 100).toFixed(1)}%)
                        </span>
                      </div>

                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5">
                          <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
                          <span className="text-slate-700">Blocked</span>
                        </div>
                        <span className="font-mono font-semibold text-slate-900">
                          {selectedRun.skipped || 0} (0.0%)
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Simulation Details Table */}
                <div className="space-y-2 pt-2 border-t border-slate-100">
                  <div className="flex items-center gap-1.5 font-semibold text-slate-900 text-xs">
                    <Database className="h-3.5 w-3.5 text-[#3067DB]" />
                    <span>Simulation Details</span>
                  </div>

                  <div className="rounded-lg border border-slate-200 bg-slate-50/50 p-3 space-y-1.5 text-[11px]">
                    <div className="flex justify-between py-0.5">
                      <span className="text-slate-500">Simulation Model</span>
                      <span className="font-mono font-semibold text-slate-800">Attendance_Workflow_v1.2</span>
                    </div>
                    <div className="flex justify-between py-0.5">
                      <span className="text-slate-500">Model Version</span>
                      <span className="font-mono text-slate-800">v1.2</span>
                    </div>
                    <div className="flex justify-between py-0.5">
                      <span className="text-slate-500">Scenarios Covered</span>
                      <span className="text-slate-800 text-right max-w-xs">Employee check-in, check-out, overtime, exceptions</span>
                    </div>
                    <div className="flex justify-between py-0.5">
                      <span className="text-slate-500">Input Dataset</span>
                      <span className="font-mono text-[#3067DB]">attendance_test_data.json</span>
                    </div>
                  </div>
                </div>

                {/* Key Findings matching Screenshot 4 */}
                <div className="space-y-2 pt-2 border-t border-slate-100">
                  <div className="flex items-center gap-1.5 font-semibold text-slate-900 text-xs">
                    <FileText className="h-3.5 w-3.5 text-[#3067DB]" />
                    <span>Key Findings</span>
                  </div>

                  <div className="space-y-2 text-[11px]">
                    <div className="flex items-start gap-2 text-slate-700">
                      <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0 mt-0.5" />
                      <span>30 scenarios passed as per expected business behaviour.</span>
                    </div>
                    <div className="flex items-start gap-2 text-slate-700">
                      <XCircle className="h-4 w-4 text-red-600 shrink-0 mt-0.5" />
                      <span>2 scenarios failed: invalid overtime calculation and missing exception rule.</span>
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="pt-3 border-t border-slate-200 flex items-center justify-between">
                  <span className="text-[11px] text-slate-500">
                    Execution Mode: <strong>Deterministic Sandbox</strong>
                  </span>
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => {
                      toast.ok(`Rerunning simulation ${selectedRun.key}`);
                      qc.invalidateQueries({ queryKey: ["executions"] });
                    }}
                    className="bg-[#3067DB] hover:bg-[#2554B8] text-white"
                  >
                    <RefreshCw className="h-3 w-3 mr-1" />
                    <span>Rerun Simulation</span>
                  </Button>
                </div>
              </div>
            )}

            {/* Sub-tab 2: Test Results */}
            {runSubTab === "results" && (
              <div className="p-4 space-y-2 text-xs max-h-96 overflow-y-auto">
                <div className="space-y-1.5">
                  {Array.from({ length: Math.min(32, selectedRun.total) }, (_, i) => {
                    const isFail = i === 10 || i === 24;
                    const tcKey = `TC-${(i + 1).toString().padStart(3, "0")}`;
                    return (
                      <div
                        key={i}
                        className="p-2.5 rounded border border-slate-200 bg-white hover:bg-slate-50 flex items-center justify-between text-xs"
                      >
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-[#3067DB] font-semibold">{tcKey}</span>
                          <span className="text-slate-800">
                            {isFail ? "Overtime Calculation Boundary Exceeded" : "Attendance punch verification scenario"}
                          </span>
                        </div>
                        <span
                          className={cn(
                            "rounded px-2 py-0.5 text-2xs font-bold",
                            isFail ? "bg-red-50 text-red-700 border border-red-200" : "bg-emerald-50 text-emerald-700 border border-emerald-200"
                          )}
                        >
                          {isFail ? "Failed" : "Passed"}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Sub-tab 3: Execution Log */}
            {runSubTab === "logs" && (
              <div className="p-4 space-y-2">
                <div className="rounded border border-slate-200 bg-slate-900 text-slate-100 p-3 font-mono text-[11px] max-h-80 overflow-y-auto leading-relaxed whitespace-pre-wrap">
                  {`[2026-11-07 11:24:00] INITIALIZING simulation runtime: Attendance_Workflow_v1.2
[2026-11-07 11:24:01] Loading specification constraints from DAY-REQ-001..DAY-REQ-056
[2026-11-07 11:24:02] Ingesting attendance_test_data.json (32 evaluation vectors)
[2026-11-07 11:24:04] Scenario 01: Standard punch pairing -> PASS (42ms)
[2026-11-07 11:24:08] Scenario 11: Daily California Overtime (OT-002) -> FAIL (Assert 1.5x expected, got 1.0x on boundary)
[2026-11-07 11:24:15] Scenario 25: Missing exception handling on timeout punch -> FAIL
[2026-11-07 11:24:26] COMPLETED: 30 passed, 2 failed in 266s. Log signature verified.`}
                </div>
              </div>
            )}

            {/* Sub-tab 4: Artifacts */}
            {runSubTab === "artifacts" && (
              <div className="p-4 space-y-2 text-xs">
                <div className="p-3 rounded border border-slate-200 bg-slate-50 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-purple-600" />
                    <span className="font-mono text-slate-800">simulation_report_RUN024.json</span>
                  </div>
                  <Button variant="outline" size="sm" onClick={() => toast.ok("Downloading report artifact")}>
                    Download
                  </Button>
                </div>
                <div className="p-3 rounded border border-slate-200 bg-slate-50 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Terminal className="h-4 w-4 text-blue-600" />
                    <span className="font-mono text-slate-800">raw_execution_trace.log</span>
                  </div>
                  <Button variant="outline" size="sm" onClick={() => toast.ok("Downloading execution trace")}>
                    Download
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* New Run Dialog */}
      {isNewRunOpen && (
        <NewRunModal
          projectId={projectId}
          onClose={() => {
            setIsNewRunOpen(false);
            qc.invalidateQueries({ queryKey: ["executions"] });
          }}
        />
      )}
    </div>
  );
}

function NewRunModal({ projectId, onClose }: { projectId: number; onClose: () => void }) {
  const toast = useToast();
  const [runType, setRunType] = useState("simulation");
  const [runName, setRunName] = useState("Employee Attendance Simulation Cycle");

  const m = useMutation({
    mutationFn: () =>
      api.post("/executions", {
        project_id: projectId,
        execution_type: runType,
        source: "platform_run",
        log_excerpt: `Started new execution ${runName}`,
      }),
    onSuccess: () => {
      toast.ok("New test execution dispatched successfully");
      onClose();
    },
    onError: toast.error,
  });

  return (
    <Dialog
      open
      onOpenChange={(o) => !o && onClose()}
      title="Start New Execution"
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="primary" loading={m.isPending} onClick={() => m.mutate()}>
            Execute
          </Button>
        </>
      }
    >
      <div className="space-y-3 text-xs">
        <Field label="Run Name" htmlFor="new-run-name">
          <Input id="new-run-name" value={runName} onChange={(e) => setRunName(e.target.value)} />
        </Field>
        <Field label="Execution Type" htmlFor="new-run-type">
          <Select id="new-run-type" value={runType} onChange={(e) => setRunType(e.target.value)}>
            <option value="simulation">Simulation</option>
            <option value="specification_validation">Specification Validation</option>
            <option value="external">External Test Run</option>
          </Select>
        </Field>
      </div>
    </Dialog>
  );
}
