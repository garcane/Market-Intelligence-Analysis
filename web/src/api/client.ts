import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type {
  Companies,
  Correlation,
  Events,
  Explainability,
  Indices,
  Job,
  JobList,
  MarketRow,
  Meta,
  ModelReport,
  NewsPage,
  Predictions,
  Prices,
  SentimentSummary,
} from "./types";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

type Params = Record<string, string | number | undefined | null>;

export function buildUrl(path: string, params?: Params): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value !== undefined && value !== null && value !== "") query.set(key, String(value));
  }
  const qs = query.toString();
  return qs ? `${path}?${qs}` : path;
}

async function request<T>(path: string, params?: Params, init?: RequestInit): Promise<T> {
  const res = await fetch(buildUrl(path, params), init);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail || `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

const get = <T>(path: string, params?: Params) => () => request<T>(path, params);

export const useMeta = () => useQuery({ queryKey: ["meta"], queryFn: get<Meta>("/api/meta") });

export const useMarkets = () => useQuery({ queryKey: ["markets"], queryFn: get<MarketRow[]>("/api/markets") });

export const usePrices = (id: string | undefined, start?: string, end?: string) =>
  useQuery({
    queryKey: ["prices", id, start, end],
    queryFn: get<Prices>(`/api/markets/${id}/prices`, { start, end }),
    enabled: Boolean(id),
    placeholderData: keepPreviousData,
  });

export const useCorrelation = (ids?: string[]) =>
  useQuery({
    queryKey: ["correlation", ids?.join(",")],
    queryFn: get<Correlation>("/api/markets/correlation", { ids: ids?.join(",") }),
  });

export const useCompanies = () => useQuery({ queryKey: ["companies"], queryFn: get<Companies>("/api/companies") });

export const useIndices = () => useQuery({ queryKey: ["indices"], queryFn: get<Indices>("/api/indices") });

export const useEvents = () => useQuery({ queryKey: ["events"], queryFn: get<Events>("/api/events") });

export const useSentiment = (model?: string, labels?: string[]) =>
  useQuery({
    queryKey: ["sentiment", model, labels?.join(",")],
    queryFn: get<SentimentSummary>("/api/sentiment/summary", { model, labels: labels?.join(",") }),
    placeholderData: keepPreviousData,
  });

export interface NewsFilters {
  q?: string;
  entity?: string;
  source?: string;
  label?: string;
  from?: string;
  to?: string;
  page?: number;
  page_size?: number;
}

export const useNews = (filters: NewsFilters) =>
  useQuery({
    queryKey: ["news", filters],
    queryFn: get<NewsPage>("/api/news", { ...filters }),
    placeholderData: keepPreviousData,
  });

export const useModelReport = (h = 5) =>
  useQuery({ queryKey: ["model-report", h], queryFn: get<ModelReport>("/api/models/report", { h }) });

export const useExplainability = (h = 5) =>
  useQuery({ queryKey: ["explainability", h], queryFn: get<Explainability>("/api/models/explainability", { h }) });

export const usePredictions = (h = 5) =>
  useQuery({ queryKey: ["predictions", h], queryFn: get<Predictions>("/api/predictions/latest", { h }) });

export const useJobs = (enabled: boolean) =>
  useQuery({
    queryKey: ["jobs"],
    queryFn: get<JobList>("/api/pipeline/jobs"),
    enabled,
    refetchInterval: (query) => (query.state.data?.running ? 2000 : false),
  });

export const useJob = (id: string | null) =>
  useQuery({
    queryKey: ["job", id],
    queryFn: get<Job>(`/api/pipeline/jobs/${id}`),
    enabled: Boolean(id),
    refetchInterval: (query) => (query.state.data?.status === "running" ? 1500 : false),
  });

export function useRunJob() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ name, maxRequests }: { name: string; maxRequests?: number }) =>
      request<Job>(`/api/pipeline/run/${name}`, undefined, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(maxRequests ? { max_requests: maxRequests } : {}),
      }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["jobs"] }),
  });
}

export const figureUrl = (name: string) => `/api/figures/${encodeURIComponent(name)}`;
