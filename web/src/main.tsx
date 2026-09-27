import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { lazy, StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
import { ThemeProvider } from "./lib/theme";
import "./theme/index.css";

const Overview = lazy(() => import("./pages/Overview"));
const AiMarket = lazy(() => import("./pages/AiMarket"));
const Stocks = lazy(() => import("./pages/Stocks"));
const Risk = lazy(() => import("./pages/Risk"));
const Companies = lazy(() => import("./pages/Companies"));
const SupplyChain = lazy(() => import("./pages/SupplyChain"));
const Energy = lazy(() => import("./pages/Energy"));
const Events = lazy(() => import("./pages/Events"));
const Sentiment = lazy(() => import("./pages/Sentiment"));
const News = lazy(() => import("./pages/News"));
const Models = lazy(() => import("./pages/Models"));
const Explainability = lazy(() => import("./pages/Explainability"));
const Predictions = lazy(() => import("./pages/Predictions"));
const Pipeline = lazy(() => import("./pages/Pipeline"));
const NotFound = lazy(() => import("./pages/NotFound"));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      refetchOnWindowFocus: false,
      retry: (count, error) => count < 2 && !(error && "status" in error && (error as { status: number }).status === 404),
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route index element={<Overview />} />
              <Route path="ai-market" element={<AiMarket />} />
              <Route path="stocks" element={<Stocks />} />
              <Route path="stocks/:id" element={<Stocks />} />
              <Route path="risk" element={<Risk />} />
              <Route path="companies" element={<Companies />} />
              <Route path="supply-chain" element={<SupplyChain />} />
              <Route path="energy" element={<Energy />} />
              <Route path="events" element={<Events />} />
              <Route path="sentiment" element={<Sentiment />} />
              <Route path="news" element={<News />} />
              <Route path="models" element={<Models />} />
              <Route path="explainability" element={<Explainability />} />
              <Route path="predictions" element={<Predictions />} />
              <Route path="pipeline" element={<Pipeline />} />
              <Route path="*" element={<NotFound />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  </StrictMode>,
);
