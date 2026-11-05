import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { DataTable } from "@/components/DataTable";
import { Badge, ErrorState } from "@/components/ui";
import { useListState } from "@/hooks/useListState";
import { ApiError } from "@/services/api";

test("status badges label historical and platform runs distinctly", () => {
  render(<><Badge value="historical_import" /><Badge value="platform_run" /><Badge value="needs_reapproval" /></>);
  expect(screen.getByText("Historical import")).toBeInTheDocument();
  expect(screen.getByText("Platform run")).toBeInTheDocument();
  expect(screen.getByText("Needs reapproval")).toBeInTheDocument();
});

test("error state shows the trace id and a permission-specific message", () => {
  render(<ErrorState error={new ApiError(403, "forbidden", "Permission 'test.review' required", null, "abc123")} />);
  expect(screen.getByText("You don't have access to this")).toBeInTheDocument();
  expect(screen.getByText(/Trace ID abc123/)).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();
});

function Table({ onSort }: { onSort: (s: string) => void }) {
  const st = useListState([], { sort: "key" });
  onSort(`${st.sort}:${st.order}:${st.page}`);
  return <DataTable state={st} query={{ data: { items: [{ id: 1, key: "TC-PAY-0001" }, { id: 2, key: "TC-PAY-0002" }], total: 60, page: st.page, page_size: 25 },
    isLoading: false, error: null, refetch: () => {} }} selectable bulkActions={(ids) => <span>bulk {ids.length}</span>}
    columns={[{ id: "key", header: "ID", sortKey: "key", cell: (r) => r.key }]} />;
}

test("server-side table: sorting, paging and row selection drive state", async () => {
  const seen: string[] = [];
  render(<MemoryRouter><Table onSort={(s) => seen.push(s)} /></MemoryRouter>);
  expect(screen.getByText("Page 1 of 3")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Next page" }));
  expect(screen.getByText("Page 2 of 3")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Sort by ID" }));
  expect(seen.at(-1)).toBe("key:asc:1");
  await userEvent.click(screen.getAllByRole("checkbox", { name: "Select row" })[0]);
  expect(screen.getByText("bulk 1")).toBeInTheDocument();
});
