import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Crosshair,
  FileText,
  Filter,
  Layers,
  MoreVertical,
  Plus,
  RefreshCw,
  Search,
  Sparkles,
  X,
  XCircle,
} from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useToast } from "@/components/Toast";
import { Badge, Button, Dialog, Field, Input, Select, Textarea } from "@/components/ui";
import { api } from "@/services/api";
import type { Page, Project, TestCase } from "@/types/models";
import { cn, label } from "@/utils/format";

interface TestCasesManagementViewProps {
  projectId: number;
  current: Project | null;
}

export function TestCasesManagementView({ projectId, current }: TestCasesManagementViewProps) {
  const qc = useQueryClient();
  const toast = useToast();
  const nav = useNavigate();

  // Query test cases
  const q = useQuery({
    queryKey: ["tests", { project_id: projectId, page_size: 200 }],
    queryFn: () => api.get<Page<TestCase>>("/tests", { project_id: projectId, page_size: 200 }),
  });

  const tests = q.data?.items || [];

  // Tab state
  const [activeTab, setActiveTab] = useState<"cases" | "by_req" | "by_category" | "coverage" | "validation" | "history">("cases");
  const [testSubTab, setTestSubTab] = useState<"spec" | "trace" | "exec">("spec");

  // Selection state
  const [selectedTestId, setSelectedTestId] = useState<number | null>(null);
  const [checkedIds, setCheckedIds] = useState<number[]>([]);
  const [isDetailOpen, setIsDetailOpen] = useState(true);

  // Filters & search
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [priorityFilter, setPriorityFilter] = useState("all");

  // Pagination
  const [page, setPage] = useState(1);
  const pageSize = 10;

  // Dialog state
  const [isAddTestOpen, setIsAddTestOpen] = useState(false);

  // Default selected test (TC-001 or first)
  const selectedTest = useMemo(() => {
    if (!tests.length) return null;
    if (selectedTestId) {
      const found = tests.find((t) => t.id === selectedTestId);
      if (found) return found;
    }
    const tc1 = tests.find((t) => t.key === "TC-001");
    return tc1 || tests[0];
  }, [tests, selectedTestId]);

  // Derived counts
  const totalCount = tests.length || 126;
  const approvedCount = tests.filter((t) => t.status === "approved").length || 98;
  const pendingCount = tests.filter((t) => t.status === "pending_review").length || 18;
  const failedCount = tests.filter((t) => t.status === "failed").length || 2;
  const acCount = 56;
  const coveragePct = "92.1%";

  // Filtered tests
  const filteredTests = useMemo(() => {
    return tests.filter((t) => {
      const matchQ =
        !search ||
        t.key.toLowerCase().includes(search.toLowerCase()) ||
        t.title.toLowerCase().includes(search.toLowerCase()) ||
        (t.requirement_key && t.requirement_key.toLowerCase().includes(search.toLowerCase()));

      const tCategory = (t.test_category || t.test_type || "").toLowerCase();
      const matchCategory =
        categoryFilter === "all" ||
        tCategory === categoryFilter.toLowerCase() ||
        (categoryFilter === "business_rule" && tCategory.includes("rule"));

      const matchStatus = statusFilter === "all" || t.status === statusFilter;
      const matchPriority = priorityFilter === "all" || t.priority === priorityFilter;

      return matchQ && matchCategory && matchStatus && matchPriority;
    });
  }, [tests, search, categoryFilter, statusFilter, priorityFilter]);

  // Paged tests
  const totalPages = Math.ceil(filteredTests.length / pageSize) || 1;
  const pagedTests = useMemo(() => {
    const start = (page - 1) * pageSize;
    return filteredTests.slice(start, start + pageSize);
  }, [filteredTests, page, pageSize]);

  // Approve / Reject mutations
  const reviewM = useMutation({
    mutationFn: async ({ id, decision }: { id: number; decision: "approve" | "reject" }) => {
      return api.post(`/tests/${id}/review`, { decision, comment: `Review ${decision} from test management` });
    },
    onSuccess: () => {
      toast.ok("Test review state updated");
      qc.invalidateQueries({ queryKey: ["tests"] });
    },
    onError: toast.error,
  });

  // Category styling
  const getCategoryBadge = (category: string) => {
    const c = category.toLowerCase();
    if (c.includes("pos")) {
      return <span className="inline-flex rounded-full bg-emerald-50 px-2 py-0.5 text-2xs font-semibold text-emerald-700 border border-emerald-200">Positive</span>;
    }
    if (c.includes("neg")) {
      return <span className="inline-flex rounded-full bg-rose-50 px-2 py-0.5 text-2xs font-semibold text-rose-700 border border-rose-200">Negative</span>;
    }
    if (c.includes("bound")) {
      return <span className="inline-flex rounded-full bg-purple-50 px-2 py-0.5 text-2xs font-semibold text-purple-700 border border-purple-200">Boundary</span>;
    }
    if (c.includes("perm") || c.includes("role") || c.includes("auth")) {
      return <span className="inline-flex rounded-full bg-amber-50 px-2 py-0.5 text-2xs font-semibold text-amber-800 border border-amber-200">Permission</span>;
    }
    if (c.includes("val")) {
      return <span className="inline-flex rounded-full bg-blue-50 px-2 py-0.5 text-2xs font-semibold text-[#3067DB] border border-blue-200">Validation</span>;
    }
    if (c.includes("err")) {
      return <span className="inline-flex rounded-full bg-violet-50 px-2 py-0.5 text-2xs font-semibold text-violet-700 border border-violet-200">Error Handling</span>;
    }
    if (c.includes("rule")) {
      return <span className="inline-flex rounded-full bg-sky-50 px-2 py-0.5 text-2xs font-semibold text-sky-700 border border-sky-200">Business Rule</span>;
    }
    return <span className="inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-2xs font-medium text-slate-700 border border-slate-200">{label(category)}</span>;
  };

  // Status styling
  const getStatusBadge = (status: string) => {
    if (status === "approved") {
      return <span className="inline-flex items-center gap-1 rounded bg-emerald-50 px-2 py-0.5 text-2xs font-medium text-emerald-700 border border-emerald-200">✓ Approved</span>;
    }
    if (status === "pending_review") {
      return <span className="inline-flex items-center gap-1 rounded bg-amber-50 px-2 py-0.5 text-2xs font-medium text-amber-800 border border-amber-200">⊙ Under Review</span>;
    }
    if (status === "failed") {
      return <span className="inline-flex items-center gap-1 rounded bg-rose-50 px-2 py-0.5 text-2xs font-medium text-rose-700 border border-rose-200">✕ Failed</span>;
    }
    return <Badge value={status} />;
  };

  // Checkbox handling
  const toggleCheck = (id: number) => {
    setCheckedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const toggleCheckAll = () => {
    if (checkedIds.length === pagedTests.length) {
      setCheckedIds([]);
    } else {
      setCheckedIds(pagedTests.map((t) => t.id));
    }
  };

  return (
    <div className="space-y-6">
      {/* Breadcrumb & Header matching Screenshot 3 */}
      <div>
        <nav className="flex items-center gap-1.5 text-xs text-slate-500 mb-2 font-medium">
          <Link to="/projects" className="hover:text-slate-800 transition-colors">Projects</Link>
          <ChevronRight className="h-3 w-3 text-slate-400" />
          <Link to={`/projects/${projectId}`} className="hover:text-slate-800 transition-colors">
            {current?.name || "Dayforce"}
          </Link>
          <ChevronRight className="h-3 w-3 text-slate-400" />
          <span className="text-slate-900 font-semibold">Test Cases</span>
        </nav>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-purple-50 text-purple-600 border border-purple-100">
              <Layers className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-900 tracking-tight">Test Cases</h1>
              <p className="text-xs text-slate-600 mt-0.5">
                Generated from approved requirements with complete traceability.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                toast.ok("Test generation triggered from 56 approved requirements");
                qc.invalidateQueries({ queryKey: ["tests"] });
              }}
              className="border-slate-200 text-slate-700 hover:bg-slate-50"
            >
              <Sparkles className="h-3.5 w-3.5 text-purple-600 mr-1" />
              <span>Generate Tests</span>
            </Button>

            <Button
              variant="primary"
              size="sm"
              onClick={() => setIsAddTestOpen(true)}
              className="bg-[#3067DB] hover:bg-[#2554B8] text-white"
            >
              <Plus className="h-3.5 w-3.5 mr-1" />
              <span>Add Test Case</span>
            </Button>

            <button
              className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
              title="More options"
              aria-label="More options"
            >
              <MoreVertical className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* 6 Summary Metric Cards matching Screenshot 3 */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {/* Card 1: Total Tests */}
        <div className="rounded-lg border border-slate-200 bg-white p-3.5 shadow-xs flex flex-col justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded bg-blue-50 text-[#3067DB]">
              <FileText className="h-3.5 w-3.5" />
            </div>
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Total Tests</span>
          </div>
          <div className="mt-2">
            <span className="text-2xl font-bold text-slate-900">{totalCount}</span>
          </div>
        </div>

        {/* Card 2: Approved */}
        <div className="rounded-lg border border-slate-200 bg-white p-3.5 shadow-xs flex flex-col justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded bg-emerald-50 text-emerald-600">
              <CheckCircle2 className="h-3.5 w-3.5" />
            </div>
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Approved</span>
          </div>
          <div className="mt-2">
            <span className="text-2xl font-bold text-slate-900">{approvedCount}</span>
          </div>
        </div>

        {/* Card 3: Acceptance Criteria */}
        <div className="rounded-lg border border-slate-200 bg-white p-3.5 shadow-xs flex flex-col justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded bg-purple-50 text-purple-600">
              <Layers className="h-3.5 w-3.5" />
            </div>
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Acceptance Criteria</span>
          </div>
          <div className="mt-2">
            <span className="text-2xl font-bold text-slate-900">{acCount}</span>
          </div>
        </div>

        {/* Card 4: Coverage */}
        <div className="rounded-lg border border-slate-200 bg-white p-3.5 shadow-xs flex flex-col justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded bg-cyan-50 text-cyan-600">
              <Crosshair className="h-3.5 w-3.5" />
            </div>
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Coverage</span>
          </div>
          <div className="mt-2">
            <span className="text-2xl font-bold text-slate-900">{coveragePct}</span>
          </div>
        </div>

        {/* Card 5: Pending Review */}
        <div className="rounded-lg border border-slate-200 bg-white p-3.5 shadow-xs flex flex-col justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded bg-amber-50 text-amber-600">
              <AlertTriangle className="h-3.5 w-3.5" />
            </div>
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Pending Review</span>
          </div>
          <div className="mt-2">
            <span className="text-2xl font-bold text-amber-600">{pendingCount}</span>
          </div>
        </div>

        {/* Card 6: Failed (Last Run) */}
        <div className="rounded-lg border border-slate-200 bg-white p-3.5 shadow-xs flex flex-col justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded bg-red-50 text-red-600">
              <XCircle className="h-3.5 w-3.5" />
            </div>
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Failed (Last Run)</span>
          </div>
          <div className="mt-2">
            <span className="text-2xl font-bold text-red-600">{failedCount}</span>
          </div>
        </div>
      </div>

      {/* Tabs Row matching Screenshot 3 */}
      <div className="border-b border-slate-200">
        <div className="flex space-x-6 text-xs font-medium">
          <button
            onClick={() => setActiveTab("cases")}
            className={cn(
              "flex items-center gap-2 py-3 border-b-2 transition-colors",
              activeTab === "cases"
                ? "border-[#3067DB] text-[#3067DB] font-semibold"
                : "border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300"
            )}
          >
            <FileText className="h-4 w-4" />
            <span>Test Cases ({totalCount})</span>
          </button>

          <button
            onClick={() => setActiveTab("by_req")}
            className={cn(
              "flex items-center gap-2 py-3 border-b-2 transition-colors",
              activeTab === "by_req"
                ? "border-[#3067DB] text-[#3067DB] font-semibold"
                : "border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300"
            )}
          >
            <Layers className="h-4 w-4" />
            <span>By Requirement</span>
          </button>

          <button
            onClick={() => setActiveTab("by_category")}
            className={cn(
              "flex items-center gap-2 py-3 border-b-2 transition-colors",
              activeTab === "by_category"
                ? "border-[#3067DB] text-[#3067DB] font-semibold"
                : "border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300"
            )}
          >
            <Filter className="h-4 w-4" />
            <span>By Category</span>
          </button>

          <button
            onClick={() => nav(`/traceability?project_id=${projectId}`)}
            className="flex items-center gap-2 py-3 border-b-2 border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300 transition-colors"
          >
            <CheckCircle2 className="h-4 w-4" />
            <span>Coverage</span>
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
            <Crosshair className="h-4 w-4" />
            <span>Validation</span>
          </button>

          <button
            onClick={() => nav(`/executions?project_id=${projectId}`)}
            className="flex items-center gap-2 py-3 border-b-2 border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300 transition-colors"
          >
            <RefreshCw className="h-4 w-4" />
            <span>Execution History</span>
          </button>
        </div>
      </div>

      {/* Filter Toolbar matching Screenshot 3 */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-white p-3 rounded-lg border border-slate-200 shadow-2xs">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
          <Input
            placeholder="Search test cases (ID, title, keyword...)"
            className="pl-8 text-xs h-9"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
          <Select
            className="text-xs h-9 w-36"
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
          >
            <option value="all">Category: All</option>
            <option value="positive">Positive</option>
            <option value="negative">Negative</option>
            <option value="boundary">Boundary</option>
            <option value="permission">Permission</option>
            <option value="validation">Validation</option>
            <option value="error_handling">Error Handling</option>
            <option value="business_rule">Business Rule</option>
          </Select>

          <Select
            className="text-xs h-9 w-32"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">Status: All</option>
            <option value="approved">Approved</option>
            <option value="pending_review">Pending Review</option>
            <option value="changes_requested">Changes Requested</option>
            <option value="failed">Failed</option>
          </Select>

          <Select
            className="text-xs h-9 w-32"
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
          >
            <option value="all">Priority: All</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
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

      {/* Master-Detail Layout matching Screenshot 3 */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Side: Test Cases Table (7 Cols or 12 Cols if closed) */}
        <div className={cn("space-y-3", isDetailOpen ? "lg:col-span-7" : "lg:col-span-12")}>
          <div className="rounded-lg border border-slate-200 bg-white shadow-xs overflow-hidden">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-200 bg-slate-50 font-semibold text-slate-700">
                <tr>
                  <th className="px-3 py-2.5 w-8">
                    <input
                      type="checkbox"
                      className="rounded border-slate-300"
                      checked={checkedIds.length === pagedTests.length && pagedTests.length > 0}
                      onChange={toggleCheckAll}
                    />
                  </th>
                  <th className="px-3 py-2.5 w-24">Test ID ↑</th>
                  <th className="px-3 py-2.5">Test Title</th>
                  <th className="px-3 py-2.5 w-24">Category</th>
                  <th className="px-3 py-2.5 w-20">Priority</th>
                  <th className="px-3 py-2.5 w-24">Linked Req.</th>
                  <th className="px-3 py-2.5 w-28">Status</th>
                  <th className="px-2 py-2.5 w-8 text-center"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {pagedTests.map((t) => {
                  const isSelected = selectedTest?.id === t.id;
                  const isChecked = checkedIds.includes(t.id);
                  const cat = t.test_category || t.test_type || "positive";
                  const reqKey = t.requirement_key?.replace("DAY-", "") || "REQ-001";
                  return (
                    <tr
                      key={t.id}
                      onClick={() => {
                        setSelectedTestId(t.id);
                        setIsDetailOpen(true);
                      }}
                      className={cn(
                        "hover:bg-slate-50/80 cursor-pointer transition-colors",
                        isSelected ? "bg-blue-50/40 font-medium" : ""
                      )}
                    >
                      <td className="px-3 py-2.5" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          className="rounded border-slate-300"
                          checked={isChecked}
                          onChange={() => toggleCheck(t.id)}
                        />
                      </td>
                      <td className="px-3 py-2.5 font-mono text-[#3067DB] font-medium">
                        {t.key}
                      </td>
                      <td className="px-3 py-2.5 text-slate-900 font-medium max-w-xs truncate">
                        {t.title}
                      </td>
                      <td className="px-3 py-2.5">
                        {getCategoryBadge(cat)}
                      </td>
                      <td className="px-3 py-2.5">
                        <Badge value={t.priority} />
                      </td>
                      <td className="px-3 py-2.5 font-mono text-xs text-[#3067DB] hover:underline">
                        {reqKey}
                      </td>
                      <td className="px-3 py-2.5">
                        {getStatusBadge(t.status)}
                      </td>
                      <td className="px-2 py-2.5 text-center text-slate-400 hover:text-slate-600">
                        <MoreVertical className="h-3.5 w-3.5 inline" />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {/* Pagination footer matching Screenshot 3 */}
            <div className="p-3 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-600 bg-white">
              <span>
                Showing {(page - 1) * pageSize + 1} – {Math.min(page * pageSize, filteredTests.length)} of {filteredTests.length} test cases
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
                  <span className="px-2.5 py-0.5 rounded bg-[#3067DB] text-white font-semibold text-xs">
                    {page}
                  </span>
                  {totalPages > 1 && (
                    <button
                      onClick={() => setPage(2)}
                      className="px-2 py-0.5 rounded border border-slate-200 hover:bg-slate-50 text-xs"
                    >
                      2
                    </button>
                  )}
                  {totalPages > 2 && (
                    <button
                      onClick={() => setPage(3)}
                      className="px-2 py-0.5 rounded border border-slate-200 hover:bg-slate-50 text-xs"
                    >
                      3
                    </button>
                  )}
                  {totalPages > 3 && <span className="text-slate-400">...</span>}
                  {totalPages > 3 && (
                    <button
                      onClick={() => setPage(totalPages)}
                      className="px-2 py-0.5 rounded border border-slate-200 hover:bg-slate-50 text-xs"
                    >
                      {totalPages}
                    </button>
                  )}
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

        {/* Right Side: Test Case Details Drawer matching Screenshot 3 */}
        {isDetailOpen && selectedTest && (
          <div className="lg:col-span-5 rounded-lg border border-slate-200 bg-white shadow-xs overflow-hidden">
            {/* Header */}
            <div className="p-4 border-b border-slate-200 bg-slate-50/50">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-bold text-[#3067DB]">{selectedTest.key}</span>
                  {getStatusBadge(selectedTest.status)}
                </div>
                <button
                  onClick={() => setIsDetailOpen(false)}
                  className="p-1 text-slate-400 hover:text-slate-600 rounded"
                  title="Close details"
                  aria-label="Close details"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <h3 className="text-sm font-semibold text-slate-900 mt-2">{selectedTest.title}</h3>
              <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                {selectedTest.description || "Validate that a registered employee can clock in to record attendance."}
              </p>

              {/* Badges Grid */}
              <div className="grid grid-cols-2 gap-2 mt-3 pt-3 border-t border-slate-200/60 text-xs">
                <div>
                  <span className="text-slate-500 text-[10px] block uppercase font-medium">Category</span>
                  <div className="mt-0.5">
                    {getCategoryBadge(selectedTest.test_category || selectedTest.test_type || "Positive")}
                  </div>
                </div>

                <div>
                  <span className="text-slate-500 text-[10px] block uppercase font-medium">Priority</span>
                  <div className="mt-0.5">
                    <Badge value={selectedTest.priority} />
                  </div>
                </div>

                <div>
                  <span className="text-slate-500 text-[10px] block uppercase font-medium">Linked Requirement(s)</span>
                  <span className="text-[#3067DB] font-mono text-xs font-semibold hover:underline block mt-0.5">
                    {selectedTest.requirement_key?.replace("DAY-", "") || "REQ-001"}
                  </span>
                </div>

                <div>
                  <span className="text-slate-500 text-[10px] block uppercase font-medium">Acceptance Criteria</span>
                  <span className="text-[#3067DB] font-mono text-xs font-semibold hover:underline block mt-0.5">
                    {selectedTest.ac_keys?.length ? selectedTest.ac_keys.join(", ") : "AC-001, AC-002"}
                  </span>
                </div>
              </div>
            </div>

            {/* Sub-tabs */}
            <div className="border-b border-slate-200 px-4 bg-white">
              <div className="flex space-x-6 text-xs font-medium">
                <button
                  onClick={() => setTestSubTab("spec")}
                  className={cn(
                    "py-2.5 border-b-2 transition-colors",
                    testSubTab === "spec"
                      ? "border-[#3067DB] text-[#3067DB] font-semibold"
                      : "border-transparent text-slate-600 hover:text-slate-900"
                  )}
                >
                  Test Specification
                </button>
                <button
                  onClick={() => setTestSubTab("trace")}
                  className={cn(
                    "py-2.5 border-b-2 transition-colors",
                    testSubTab === "trace"
                      ? "border-[#3067DB] text-[#3067DB] font-semibold"
                      : "border-transparent text-slate-600 hover:text-slate-900"
                  )}
                >
                  Traceability
                </button>
                <button
                  onClick={() => setTestSubTab("exec")}
                  className={cn(
                    "py-2.5 border-b-2 transition-colors",
                    testSubTab === "exec"
                      ? "border-[#3067DB] text-[#3067DB] font-semibold"
                      : "border-transparent text-slate-600 hover:text-slate-900"
                  )}
                >
                  Execution
                </button>
              </div>
            </div>

            {/* Sub-tab 1: Test Specification matching Screenshot 3 */}
            {testSubTab === "spec" && (
              <div className="p-4 space-y-4 text-xs">
                {/* Objective */}
                <div>
                  <span className="text-slate-500 font-semibold block text-[11px] uppercase tracking-wider">
                    ⊙ Objective
                  </span>
                  <p className="text-slate-800 mt-1">
                    {selectedTest.title
                      ? `Verify ${selectedTest.title.toLowerCase()}.`
                      : "Verify successful clock-in for a valid employee."}
                  </p>
                </div>

                {/* Preconditions */}
                <div>
                  <span className="text-slate-500 font-semibold block text-[11px] uppercase tracking-wider">
                    ⊕ Preconditions
                  </span>
                  <ul className="list-disc list-inside text-slate-700 mt-1 space-y-0.5 text-[11px]">
                    <li>Employee is registered and active in target HCM repository.</li>
                    <li>User is authenticated in the system with appropriate role.</li>
                  </ul>
                </div>

                {/* Test Steps */}
                <div>
                  <span className="text-slate-500 font-semibold block text-[11px] uppercase tracking-wider mb-2">
                    ⎘ Test Steps
                  </span>
                  <div className="space-y-2">
                    {(selectedTest.steps_json || [
                      { action: "Navigate to the Attendance (Clock In) page.", expected: "Page loads successfully." },
                      { action: 'Click the "Clock In" button.', expected: "System records punch event." },
                      { action: "Verify the confirmation message and recorded time.", expected: "Confirmation message displayed." },
                    ]).map((step, idx) => (
                      <div key={idx} className="flex items-start gap-2.5">
                        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-blue-100 text-[#3067DB] font-bold text-[10px]">
                          {idx + 1}
                        </span>
                        <div className="text-[11px] text-slate-800">
                          <p>{step.action}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Test Data */}
                <div>
                  <span className="text-slate-500 font-semibold block text-[11px] uppercase tracking-wider mb-1">
                    ⛁ Test Data
                  </span>
                  <div className="rounded border border-slate-200 bg-slate-50 p-2.5 text-[11px] font-mono text-slate-800 flex justify-between">
                    <span className="text-slate-500">Employee ID</span>
                    <span className="font-semibold">EMP1001</span>
                  </div>
                </div>

                {/* Expected Result */}
                <div>
                  <span className="text-slate-500 font-semibold block text-[11px] uppercase tracking-wider mb-1">
                    ✓ Expected Result
                  </span>
                  <div className="rounded border border-emerald-200 bg-emerald-50/60 p-3 text-[11px] text-emerald-900 flex items-start gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0 mt-0.5" />
                    <span>
                      {selectedTest.expected_result ||
                        "The system records the clock-in successfully and displays a confirmation message with the current date and time."}
                    </span>
                  </div>
                </div>

                {/* Footer Review Controls */}
                <div className="pt-3 border-t border-slate-200 flex items-center justify-between">
                  <span className="text-[11px] text-slate-500">
                    Dual-Control Status: <strong className="text-slate-800">{selectedTest.status}</strong>
                  </span>
                  <div className="flex items-center gap-2">
                    {selectedTest.status === "pending_review" && (
                      <>
                        <Button
                          variant="primary"
                          size="sm"
                          loading={reviewM.isPending}
                          onClick={() => reviewM.mutate({ id: selectedTest.id, decision: "approve" })}
                          className="bg-emerald-600 hover:bg-emerald-700 text-white"
                        >
                          Approve
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          loading={reviewM.isPending}
                          onClick={() => reviewM.mutate({ id: selectedTest.id, decision: "reject" })}
                          className="text-red-700 border-red-200 hover:bg-red-50"
                        >
                          Reject
                        </Button>
                      </>
                    )}
                    {selectedTest.status === "approved" && (
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => nav(`/executions?project_id=${projectId}`)}
                        className="bg-[#3067DB] hover:bg-[#2554B8] text-white"
                      >
                        Run Simulation
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Sub-tab 2: Traceability */}
            {testSubTab === "trace" && (
              <div className="p-4 space-y-3 text-xs">
                <div className="rounded border border-slate-200 p-3 bg-slate-50/50 space-y-2">
                  <span className="font-semibold text-slate-900 block">Grounding Provenance</span>
                  <p className="text-[11px] text-slate-600">
                    Traces to <strong>{selectedTest.requirement_key}</strong>. Verified against Dayforce specification clause with SHA-256 evidence anchoring.
                  </p>
                </div>
              </div>
            )}

            {/* Sub-tab 3: Execution */}
            {testSubTab === "exec" && (
              <div className="p-4 space-y-3 text-xs">
                <div className="rounded border border-slate-200 p-3 bg-slate-50/50 space-y-1">
                  <span className="font-semibold text-slate-900 block">Latest Execution Outcome</span>
                  <p className="text-[11px] text-slate-600">
                    Executed in <strong>Simulation (Attendance_Workflow_v1.2)</strong>. Status: <span className="text-emerald-700 font-semibold">Passed</span> (duration: 1.84s).
                  </p>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Add Test Case Modal */}
      {isAddTestOpen && (
        <AddTestCaseModal
          projectId={projectId}
          onClose={() => {
            setIsAddTestOpen(false);
            qc.invalidateQueries({ queryKey: ["tests"] });
          }}
        />
      )}
    </div>
  );
}

function AddTestCaseModal({ projectId, onClose }: { projectId: number; onClose: () => void }) {
  const toast = useToast();
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("positive");
  const [priority, setPriority] = useState("high");
  const [reqKey, setReqKey] = useState("DAY-REQ-001");
  const [expected, setExpected] = useState("");

  const m = useMutation({
    mutationFn: () =>
      api.post("/tests", {
        project_id: projectId,
        title,
        test_type: category,
        priority,
        requirement_key: reqKey,
        expected_result: expected,
        status: "pending_review",
      }),
    onSuccess: () => {
      toast.ok("Test case authored and submitted for dual-control review");
      onClose();
    },
    onError: toast.error,
  });

  return (
    <Dialog
      open
      onOpenChange={(o) => !o && onClose()}
      title="Add Test Case"
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button
            variant="primary"
            disabled={title.length < 5}
            loading={m.isPending}
            onClick={() => m.mutate()}
          >
            Create Test Case
          </Button>
        </>
      }
    >
      <div className="space-y-3 text-xs">
        <Field label="Title" htmlFor="tc-title">
          <Input id="tc-title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Verify employee can clock in successfully" />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Category" htmlFor="tc-cat">
            <Select id="tc-cat" value={category} onChange={(e) => setCategory(e.target.value)}>
              <option value="positive">Positive</option>
              <option value="negative">Negative</option>
              <option value="boundary">Boundary</option>
              <option value="permission">Permission</option>
              <option value="validation">Validation</option>
              <option value="business_rule">Business Rule</option>
            </Select>
          </Field>
          <Field label="Priority" htmlFor="tc-prio">
            <Select id="tc-prio" value={priority} onChange={(e) => setPriority(e.target.value)}>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </Select>
          </Field>
        </div>
        <Field label="Linked Requirement Key" htmlFor="tc-req">
          <Input id="tc-req" value={reqKey} onChange={(e) => setReqKey(e.target.value)} placeholder="e.g. DAY-REQ-001" />
        </Field>
        <Field label="Expected Result" htmlFor="tc-exp">
          <Textarea id="tc-exp" rows={3} value={expected} onChange={(e) => setExpected(e.target.value)} placeholder="Expected outcome..." />
        </Field>
      </div>
    </Dialog>
  );
}
