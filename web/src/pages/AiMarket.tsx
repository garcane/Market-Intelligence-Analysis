import { createColumnHelper } from "@tanstack/react-table";
import { useMemo } from "react";

import { useIndices } from "../api/client";
import type { IndexSummary } from "../api/types";
import { Chart } from "../components/Chart";
import { DataTable } from "../components/DataTable";
import { Badge, Card, Delta, PageHeader, QueryState } from "../components/ui";
import { numFmt, pctFmt, timeSeries } from "../lib/charts";
import { humanize, num, pct } from "../lib/format";

type Row = IndexSummary & { name: string; isIndex: boolean };
const col = createColumnHelper<Row>();
const INDEX_BG = ["bg-brand-yellow", "bg-teal-light", "bg-rose-light"];
const BENCHMARKS = ["SPX", "NASDAQ", "SOXX"];

const columns = [
  col.accessor("name", {
    header: "Series",
    cell: (c) => (
      <span className="flex items-center gap-2 font-medium">
        {humanize(c.getValue())}
        {c.row.original.isIndex && <Badge tone="yellow">AI index</Badge>}
      </span>
    ),
  }),
  col.accessor("cumulative_return", { header: "Cumulative", cell: (c) => <Delta value={c.getValue()} />, meta: { align: "right" } }),
  col.accessor("annualized_volatility", { header: "Ann. vol", cell: (c) => pct(c.getValue()), meta: { align: "right" } }),
  col.accessor("max_drawdown", { header: "Max DD", cell: (c) => <span className="text-loss">{pct(c.getValue())}</span>, meta: { align: "right" } }),
  col.accessor("sharpe_ratio", { header: "Sharpe", cell: (c) => num(c.getValue()), meta: { align: "right" } }),
  col.accessor((r) => r.beta?.SPX ?? null, { id: "beta_spx", header: "β SPX", cell: (c) => num(c.getValue()), meta: { align: "right" } }),
  col.accessor((r) => r.beta?.SOXX ?? null, { id: "beta_soxx", header: "β SOXX", cell: (c) => num(c.getValue()), meta: { align: "right" } }),
  col.accessor((r) => r.beta?.BTC ?? null, { id: "beta_btc", header: "β BTC", cell: (c) => num(c.getValue()), meta: { align: "right" } }),
];

export default function AiMarket() {
  const indices = useIndices();

  const view = useMemo(() => {
    const d = indices.data;
    if (!d) return null;
    const indexNames = Object.keys(d.index_members);
    const names = [...indexNames, ...BENCHMARKS.filter((b) => d.cumulative_return[b])];
    return {
      indexNames,
      rows: Object.entries(d.indices).map(([name, s]) => ({ ...s, name, isIndex: indexNames.includes(name) })),
      cumulative: timeSeries(
        names.map((n) => ({ name: humanize(n), points: d.cumulative_return[n].map((p) => [p.date, p.value] as [string, number]) })),
        { yFormat: pctFmt(0), zoom: true, zeroLine: true },
      ),
      rolling: timeSeries(
        Object.entries(d.rolling_corr_vs_spx).map(([n, pts]) => ({ name: humanize(n), points: pts.map((p) => [p.date, p.value] as [string, number]) })),
        { yFormat: numFmt(2), zeroLine: true },
      ),
    };
  }, [indices.data]);

  return (
    <>
      <PageHeader
        title="AI market"
        description="Three equal-weighted thematic indices built from ingested constituents, compared with broad-market, semiconductor and crypto benchmarks."
      />
      <QueryState query={indices} skeleton="h-[600px]">
        {(d) => (
          <>
            <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-3">
              {view!.indexNames.map((name, i) => (
                <div key={name} className={`rounded-[28px] p-6 ${INDEX_BG[i % INDEX_BG.length]}`}>
                  <div className="text-[13px] font-medium text-charcoal/80">{humanize(name)}</div>
                  <div className="tabular mt-2 text-[32px] leading-none font-medium tracking-tight">
                    {pct(d.indices[name]?.cumulative_return, 0, true)}
                  </div>
                  <div className="mt-1 text-[13px] text-charcoal/70">cumulative · Sharpe {num(d.indices[name]?.sharpe_ratio)}</div>
                  <div className="mt-4 flex flex-wrap gap-1.5">
                    {d.index_members[name].map((m) => (
                      <span key={m} className="rounded-full bg-white/70 px-2.5 py-0.5 text-[12px] font-semibold">{m}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <Card title="Cumulative return" subtitle="AI indices against benchmarks. Click legend items to hide series." className="mb-6">
              <Chart option={view!.cumulative} height={400} ariaLabel="Cumulative return of AI indices and benchmarks" />
            </Card>

            <div className="grid grid-cols-1 gap-6 xl:grid-cols-5">
              <Card title="Risk and return" subtitle="Betas are against daily benchmark returns" className="xl:col-span-3">
                <DataTable data={view!.rows} columns={columns} initialSort={[{ id: "cumulative_return", desc: true }]} dense caption="Index risk and return" />
              </Card>
              <Card title="30-day correlation with the S&P 500" className="xl:col-span-2">
                <Chart option={view!.rolling} height={300} ariaLabel="Rolling 30-day correlation of AI indices with SPX" />
              </Card>
            </div>
          </>
        )}
      </QueryState>
    </>
  );
}
