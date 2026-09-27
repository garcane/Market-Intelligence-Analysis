import { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { useCompanies, useMarkets } from "../api/client";
import type { MarketRow, ThemeMember } from "../api/types";
import { Chart } from "../components/Chart";
import { Sparkline } from "../components/Sparkline";
import { Badge, Card, Delta, PageHeader, PillTabs, QueryState } from "../components/ui";
import { currencySuffix } from "../lib/assets";
import { horizontalBars, numFmt, pctFmt } from "../lib/charts";
import { price } from "../lib/format";

const median = (values: number[]) => {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
};

function MemberCard({ m, market }: { m: ThemeMember; market?: MarketRow }) {
  return (
    <div className="flex flex-col gap-3 rounded-card border border-hairline-soft bg-canvas p-5">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="text-[16px] font-medium">{m.name}</div>
          <div className="text-[13px] text-steel">
            {[m.kind === "etf" ? "ETF" : null, m.country, m.region].filter(Boolean).join(" · ")}
          </div>
        </div>
        {m.ticker ? (
          market
            ? <Link to={`/stocks/${m.ticker}`}><Badge tone="dark">{m.ticker}</Badge></Link>
            : <Badge>{m.ticker}</Badge>
        ) : <Badge>private</Badge>}
      </div>
      {m.subsegment && <Badge tone="teal" className="self-start">{m.subsegment}</Badge>}
      {m.role_notes && <p className="text-[14px] leading-relaxed text-slate">{m.role_notes}</p>}
      {market && (
        <Link to={`/stocks/${market.market_id}`} className="mt-auto flex items-end justify-between gap-3 rounded-2xl bg-surface p-3 hover:bg-surface/70">
          <div className="tabular text-[13px] leading-relaxed">
            <div className="font-medium text-ink">
              {price(market.last_close)}<span className="text-stone">{currencySuffix(market.currency)}</span>{" "}
              <Delta value={market.change_1d} digits={2} />
            </div>
            <div className="text-steel">Total return <Delta value={market.total_return} /></div>
          </div>
          <Sparkline values={market.spark} />
        </Link>
      )}
    </div>
  );
}

/** Segment-by-segment view of one theme (e.g. AI Supply Chain, Energy). */
export function ThemeExplorer({ theme, title, description }: { theme: string; title: string; description: string }) {
  const companies = useCompanies();
  const markets = useMarkets();
  const [params, setParams] = useSearchParams();

  const byTicker = useMemo(() => new Map((markets.data ?? []).map((m) => [m.market_id, m])), [markets.data]);

  const view = useMemo(() => {
    const d = companies.data;
    if (!d) return null;
    const segments = d.segments[theme] ?? [];
    const members = d.theme_members.filter((m) => m.theme === theme);
    const stats = segments.map((s) => {
      const inSegment = members.filter((m) => m.segment === s);
      const returns = inSegment
        .map((m) => (m.ticker ? byTicker.get(m.ticker)?.change_1d : null))
        .filter((v): v is number => typeof v === "number");
      return { segment: s, count: new Set(inSegment.map((m) => m.entity_id)).size, median1d: median(returns) };
    });
    return {
      segments,
      members,
      counts: horizontalBars(stats.map((s) => ({ label: s.segment, value: s.count })), { format: numFmt(0), color: "#0fbcb0" }),
      moves: horizontalBars(stats.map((s) => ({ label: s.segment, value: s.median1d })), { format: pctFmt(1), signed: true }),
    };
  }, [companies.data, theme, byTicker]);

  const selected = params.get("segment") ?? view?.segments[0] ?? "";
  const members = (view?.members ?? []).filter((m) => m.segment === selected);
  const priced = members.filter((m) => m.ticker && byTicker.has(m.ticker)).length;

  return (
    <>
      <PageHeader title={title} description={description} />
      <QueryState query={companies} skeleton="h-[600px]">
        {() => (
          <>
            <div className="mb-6 grid grid-cols-1 gap-6 xl:grid-cols-2">
              <Card title="Members per segment" subtitle="A company can sit in more than one segment">
                <Chart option={view!.counts} height={260} ariaLabel={`Number of members in each ${theme} segment`} />
              </Card>
              <Card title="Latest daily move" subtitle="Median 1-day return of each segment's priced members">
                <Chart option={view!.moves} height={260} ariaLabel={`Median latest daily return per ${theme} segment`} />
              </Card>
            </div>

            <div className="mb-4">
              <PillTabs
                label="Segment"
                value={selected}
                onChange={(s) => setParams({ segment: s }, { replace: true })}
                options={view!.segments.map((s) => ({ value: s, label: s }))}
              />
            </div>
            <p className="mb-4 text-[13px] text-steel">
              {members.length} members · {priced} with price data · total return is over each asset's full price history
            </p>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              {members.map((m) => (
                <MemberCard key={`${m.entity_id}-${m.segment}`} m={m} market={m.ticker ? byTicker.get(m.ticker) : undefined} />
              ))}
            </div>
          </>
        )}
      </QueryState>
    </>
  );
}
