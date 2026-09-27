import { createColumnHelper } from "@tanstack/react-table";
import { useMemo } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { useMarkets, useMeta } from "../api/client";
import type { MarketRow } from "../api/types";
import { DataTable } from "../components/DataTable";
import { Sparkline } from "../components/Sparkline";
import { Badge, Card, Delta, PageHeader, PillTabs, QueryState, StatCard } from "../components/ui";
import { asCategory, CATEGORIES, type Category, currencySuffix, inCategory, KIND_LABEL, KIND_TONE } from "../lib/assets";
import { compact, pct, price, shortDate } from "../lib/format";

const col = createColumnHelper<MarketRow>();

const columns = [
  col.accessor("name", {
    header: "Name",
    cell: (c) => (
      <div className="flex min-w-0 items-center gap-2">
        <span className="max-w-[12rem] truncate font-medium" title={c.getValue()}>{c.getValue()}</span>
        {c.row.original.rank !== null && <Badge tone="yellow">#{c.row.original.rank}</Badge>}
      </div>
    ),
  }),
  col.accessor("market_id", {
    header: "Ticker",
    cell: (c) => (
      <div className="flex items-center gap-2">
        <span className="font-semibold">{c.getValue()}</span>
        {c.row.original.modelled && <Badge tone="teal">modelled</Badge>}
      </div>
    ),
  }),
  col.accessor("kind", { header: "Type", cell: (c) => <Badge tone={KIND_TONE[c.getValue()]}>{KIND_LABEL[c.getValue()]}</Badge> }),
  col.accessor("last_close", {
    header: "Last close",
    cell: (c) => (
      <span className="whitespace-nowrap">
        {price(c.getValue())}
        <span className="text-[12px] text-stone">{currencySuffix(c.row.original.currency)}</span>
      </span>
    ),
    meta: { align: "right" },
  }),
  col.accessor("change_1d", { header: "1D", cell: (c) => <Delta value={c.getValue()} digits={2} />, meta: { align: "right" } }),
  col.accessor("total_return", { header: "Total return", cell: (c) => <Delta value={c.getValue()} />, meta: { align: "right" } }),
  col.accessor("annualized_volatility", { header: "Ann. vol", cell: (c) => pct(c.getValue()), meta: { align: "right" } }),
  col.accessor("max_drawdown", {
    header: "Max drawdown",
    cell: (c) => <span className="text-loss">{pct(c.getValue())}</span>,
    meta: { align: "right" },
  }),
  col.accessor("spark", { header: "6 months", enableSorting: false, cell: (c) => <Sparkline values={c.getValue()} /> }),
];

function historyMonths(rows: MarketRow[] | undefined): string {
  if (!rows?.length) return "—";
  const start = Math.min(...rows.map((r) => Date.parse(r.start_date)));
  const end = Math.max(...rows.map((r) => Date.parse(r.end_date)));
  return `${Math.round((end - start) / (30.44 * 86400000))} months`;
}

export default function Overview() {
  const markets = useMarkets();
  const meta = useMeta();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const filter = asCategory(params.get("category"));

  const best = useMemo(() => {
    const rows = (markets.data ?? []).filter((m) => !m.categories.includes("Benchmarks") && m.total_return !== null);
    return rows.sort((a, b) => (b.total_return ?? 0) - (a.total_return ?? 0))[0];
  }, [markets.data]);

  const rows = useMemo(
    () => (markets.data ?? []).filter((m) => inCategory(m, filter)),
    [markets.data, filter],
  );

  return (
    <>
      <PageHeader
        title="AI market overview"
        description="How stocks across the AI supply chain and energy, the top cryptocurrencies and their benchmarks have moved, with the news, sentiment and models built on top of them."
      />

      <div className="mb-6 grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
        <StatCard
          tone="yellow"
          label="Assets tracked"
          value={markets.data?.length ?? "—"}
          hint={`${markets.data?.filter((m) => m.modelled).length ?? 0} used for modelling`}
        />
        <StatCard
          tone="teal"
          label="Price history"
          value={historyMonths(markets.data)}
          hint={`to ${shortDate(meta.data?.latest_price_date)}`}
        />
        <StatCard
          tone="coral"
          label="News articles"
          value={compact(meta.data?.news_count)}
          hint={`${compact(meta.data?.scored_articles)} sentiment-scored`}
        />
        <StatCard
          tone="rose"
          label="Best performer"
          value={best?.market_id ?? "—"}
          hint={best ? `${pct(best.total_return, 0, true)} over the period` : undefined}
        />
      </div>

      <Card
        title="Assets"
        subtitle="Returns and risk over each asset's full history. Select a row for charts."
        action={
          <PillTabs<Category>
            label="Category"
            value={filter}
            onChange={(c) => setParams((p) => { if (c === "All") p.delete("category"); else p.set("category", c); return p; }, { replace: true })}
            options={CATEGORIES.map((c) => ({
              value: c,
              label: <>{c} <span className="opacity-60">{(markets.data ?? []).filter((m) => inCategory(m, c)).length}</span></>,
            }))}
          />
        }
      >
        <QueryState query={markets} skeleton="h-96">
          {() => (
            <DataTable
              data={rows}
              columns={columns}
              caption="Assets with returns and risk"
              initialSort={[{ id: "total_return", desc: true }]}
              onRowClick={(r) => navigate(`/stocks/${r.market_id}`)}
            />
          )}
        </QueryState>
      </Card>
    </>
  );
}
