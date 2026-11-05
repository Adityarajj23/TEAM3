import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "@/App";
import { ToastProvider } from "@/components/Toast";
import { AuthProvider } from "@/hooks/useAuth";
import { ApiError } from "@/services/api";
import "./index.css";

const qc = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 15_000, refetchOnWindowFocus: false,
      retry: (n, e) => !(e instanceof ApiError && [401, 403, 404, 409, 422].includes(e.status)) && n < 2 },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={qc}>
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <ToastProvider><AuthProvider><App /></AuthProvider></ToastProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
