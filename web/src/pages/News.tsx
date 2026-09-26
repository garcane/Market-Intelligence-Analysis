import { ChevronLeft, ChevronRight, ExternalLink, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { useNews, type NewsFilters } from "../api/client";
import type { NewsItem } from "../api/types";
import { Badge, Button, Card, EmptyState, ErrorState, PageHeader, Select, Skeleton, type BadgeTone } from "../components/ui";
import { humanize, relativeTime, shortDate } from "../lib/format";

const PAGE_SIZE = 20;
const LABEL_TONE: Record<string, BadgeTone> = {
  Bullish: "gain", "Slightly Bullish": "teal", Neutral: "neutral", "Slightly Bearish": "coral", Bearish: "loss",
};

function safeUrl(url: string | null): string | null {
  if (!url) return null;
  try {
    const u = new URL(url);
    return u.protocol === "https:" || u.protocol === "http:" ? u.toString() : null;
  } catch {
    return null;
  }
}

function Headline({ item }: { item: NewsItem }) {
  const href = safeUrl(item.url);
  const entity = item.entity ?? item.matched_company_id ?? item.matched_asset_id;
  return (
    <li className="border-b border-hairline-soft py-4 last:border-0">
      <div className="mb-1.5 flex flex-wrap items-center gap-2 text-[12px] text-steel">
        <span className="font-medium text-charcoal">{item.source_id ?? humanize(item.source)}</span>
        <span aria-hidden>·</span>
        <time dateTime={item.timestamp} title={shortDate(item.timestamp)}>{relativeTime(item.timestamp)}</time>
        {entity && <Badge tone="blue">{entity.toUpperCase()}</Badge>}
        {item.sentiment_label && (
          <Badge tone={LABEL_TONE[item.sentiment_label] ?? "neutral"}>
            {item.sentiment_label}
            {item.sentiment_score !== null && <span className="tabular opacity-70">{item.sentiment_score.toFixed(2)}</span>}
          </Badge>
        )}
        <span className="ml-auto text-stone">via {humanize(item.source)}</span>
      </div>
      {href ? (
        <a href={href} target="_blank" rel="noopener noreferrer nofollow" className="group inline-flex items-start gap-1.5 text-[16px] leading-snug font-medium hover:text-brand-blue">
          {item.title}
          <ExternalLink className="mt-1 size-3.5 shrink-0 opacity-40 group-hover:opacity-100" aria-hidden />
          <span className="sr-only">(opens in a new tab)</span>
        </a>
      ) : (
        <span className="text-[16px] leading-snug font-medium">{item.title}</span>
      )}
    </li>
  );
}

export default function News() {
  const [params, setParams] = useSearchParams();
  const filters: NewsFilters = {
    q: params.get("q") ?? undefined,
    entity: params.get("entity") ?? undefined,
    source: params.get("source") ?? undefined,
    label: params.get("label") ?? undefined,
    from: params.get("from") ?? undefined,
    to: params.get("to") ?? undefined,
    page: Number(params.get("page") ?? 1),
    page_size: PAGE_SIZE,
  };
  const news = useNews(filters);
  const [query, setQuery] = useState(filters.q ?? "");

  const set = (key: string, value: string) =>
    setParams((p) => {
      if (value) p.set(key, value); else p.delete(key);
      if (key !== "page") p.delete("page");
      return p;
    }, { replace: key !== "page" });

  // Debounce the search box into the URL.
  useEffect(() => {
    const t = setTimeout(() => {
      if ((params.get("q") ?? "") !== query) set("q", query);
    }, 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query]);

  const facets = news.data?.facets ?? {};
  const total = news.data?.total ?? 0;
  const page = filters.page ?? 1;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const option = (all: string, values: string[] | undefined, fmt = (v: string) => v) =>
    [{ value: "", label: all }, ...(values ?? []).map((v) => ({ value: v, label: fmt(v) }))];

  return (
    <>
      <PageHeader
        title="News feed"
        description="Every collected headline with its sentiment. Links go to the original publisher; article text is not stored here."
      />
      <Card className="mb-6">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-7">
          <label className="relative flex flex-col gap-1 text-[13px] font-medium text-steel sm:col-span-2">
            Search headlines
            <Search className="pointer-events-none absolute bottom-3 left-3 size-4 text-stone" aria-hidden />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. earnings, Blackwell, ETF"
              className="h-10 rounded-full border border-hairline-strong bg-canvas pr-4 pl-9 text-[14px] text-ink placeholder:text-muted"
            />
          </label>
          <Select label="Company / asset" value={filters.entity ?? ""} onChange={(v) => set("entity", v)}
            options={option("All", facets.entities, (v) => v.toUpperCase())} />
          <Select label="Sentiment" value={filters.label ?? ""} onChange={(v) => set("label", v)} options={option("Any", facets.labels)} />
          <Select label="Provider" value={filters.source ?? ""} onChange={(v) => set("source", v)} options={option("All", facets.sources, humanize)} />
          <div className="grid grid-cols-2 gap-2 sm:col-span-2">
            <label className="flex flex-col gap-1 text-[13px] font-medium text-steel">
              From
              <input type="date" value={filters.from ?? ""} onChange={(e) => set("from", e.target.value)}
                className="h-10 rounded-full border border-hairline-strong bg-canvas px-3 text-[13px] text-ink" />
            </label>
            <label className="flex flex-col gap-1 text-[13px] font-medium text-steel">
              To
              <input type="date" value={filters.to ?? ""} onChange={(e) => set("to", e.target.value)}
                className="h-10 rounded-full border border-hairline-strong bg-canvas px-3 text-[13px] text-ink" />
            </label>
          </div>
        </div>
      </Card>

      <Card
        title={news.data ? `${total.toLocaleString()} headlines` : "Headlines"}
        subtitle={news.data?.model ? `Sentiment from ${news.data.model}; unscored articles show no label` : undefined}
      >
        {news.isLoading ? (
          <div className="flex flex-col gap-3">{Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-14" />)}</div>
        ) : news.error ? (
          <ErrorState error={news.error} onRetry={() => news.refetch()} />
        ) : total === 0 ? (
          <EmptyState title="No headlines match">Try clearing a filter or widening the dates.</EmptyState>
        ) : (
          <>
            <ul aria-busy={news.isFetching} className={news.isFetching ? "opacity-60 transition-opacity" : ""}>
              {news.data!.items.map((item) => <Headline key={item.news_id} item={item} />)}
            </ul>
            <nav aria-label="Pagination" className="mt-4 flex items-center justify-between gap-3">
              <Button variant="secondary" disabled={page <= 1} onClick={() => set("page", String(page - 1))}>
                <ChevronLeft className="size-4" aria-hidden /> Newer
              </Button>
              <span className="tabular text-[13px] text-steel">Page {page} of {pages.toLocaleString()}</span>
              <Button variant="secondary" disabled={page >= pages} onClick={() => set("page", String(page + 1))}>
                Older <ChevronRight className="size-4" aria-hidden />
              </Button>
            </nav>
          </>
        )}
      </Card>
    </>
  );
}
