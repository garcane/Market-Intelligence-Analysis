import { createColumnHelper } from "@tanstack/react-table";
import { Info } from "lucide-react";
import { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { useCompanies, useMeta, useSentiment } from "../api/client";
import type { Coverage, SentimentSummary } from "../api/types";
import { Chart, type ChartOption } from "../components/Chart";
import { DataTable } from "../components/DataTable";
import { Card, FilterPills, PageHeader, PillTabs, QueryState, StatCard } from "../components/ui";
import { AXIS, TOOLTIP } from "../lib/chartTheme";
import { numFmt, timeSeries } from "../lib/charts";
import { compact, humanize, num, pct } from "../lib/format";

const LABEL_ORDER = ["Bearish", "Slightly Bearish", "Neutral", "Slightly Bullish", "Bullish"];
const LABEL_COLOR: Record<string, string> = {
  Bearish: "#e5484d", "Slightly Bearish": "#ff9999", Neutral: "#c7cad5", "Slightly Bullish": "#7fd8b3", Bullish: "#00b473",
};

type EntityRow = SentimentSummary["by_entity"][number];
const col = createColumnHelper<EntityRow & { name: string }>();
const entityColumns = [
  col.accessor("name", { header: "Company", cell: (c) => <span className="font-medium">{c.getValue()}</span> }),
  col.accessor("n_articles", { header: "Articles", meta: { align: "right" } }),
  col.accessor("mean_sentiment", {
    header: "Mean score",
    meta: { align: "right" },
    cell: (c) => {
      const v = c.getValue();
      return <span className={v === null ? "" : v > 0.05 ? "text-gain" : v < -0.05 ? "text-loss" : "text-slate"}>{num(v, 3)}</span>;
    },
  }),
  col.accessor("std_sentiment", { header: "Std dev", cell: (c) => num(c.getValue(), 3), meta: { align: "right" } }),
];

type Period = "train" | "validation" | "test";
const PERIODS: Period[] = ["train", "validation", "test"];

function distributionOption(d: SentimentSummary): ChartOption {
  const byLabel = new Map(d.distribution.map((r) => [r.label, r.count]));
  const labels = LABEL_ORDER.filter((l) => byLabel.has(l)).concat(d.distribution.map((r) => r.label).filter((l) => !LABEL_ORDER.includes(l)));
  return {
    grid: { left: 8, right: 8, top: 16, bottom: 8, containLabel: true },
    tooltip: { ...TOOLTIP, axisPointer: { type: "shadow" } },
    xAxis: { type: "category", data: labels, ...AXIS },
    yAxis: { type: "value", ...AXIS },
    series: [{
      type: "bar", barMaxWidth: 48, name: "Articles",
      data: labels.map((l) => ({ value: byLabel.get(l), itemStyle: { color: LABEL_COLOR[l] ?? "#4262ff", borderRadius: [6, 6, 0, 0] } })),
    }],
  };
}

function CoverageTable({ coverage }: { coverage: Coverage }) {
  const markets = Object.keys(coverage.by_market);
  const cell = (p: number | null | undefined) => (
    <span className={p && p >= 0.25 ? "text-gain" : p ? "text-charcoal" : "text-stone"}>{pct(p ?? 0, 0)}</span>
  );
  return (
    <div className="-mx-5 overflow-x-auto px-5">
      <table className="tabular w-full text-[14px]">
        <caption className="sr-only">Share of trading days with at least one article, by model split</caption>
        <thead>
          <tr className="border-b border-hairline text-[12px] font-semibold tracking-[0.3px] text-steel uppercase">
            <th scope="col" className="py-2.5 text-left">Asset</th>
            {PERIODS.map((p) => <th key={p} scope="col" className="px-3 py-2.5 text-right">{p}</th>)}
          </tr>
        </thead>
        <tbody>
          {markets.map((m) => (
            <tr key={m} className="border-b border-hairline-soft">
              <td className="py-2 font-semibold">{m}</td>
              {PERIODS.map((p) => <td key={p} className="px-3 py-2 text-right">{cell(coverage.by_market[m][p]?.pct)}</td>)}
            </tr>
          ))}
          <tr className="font-semibold">
            <td className="py-2">All</td>
            {PERIODS.map((p) => <td key={p} className="px-3 py-2 text-right">{cell(coverage.totals[p]?.pct)}</td>)}
          </tr>
        </tbody>
      </table>
    </div>
  );
}

export default function Sentiment() {
  const [params, setParams] = useSearchParams();
  const model = params.get("model") ?? undefined;
  const labels = params.get("labels")?.split("|").filter(Boolean) ?? [];
  const sentiment = useSentiment(model, labels.length ? labels : undefined);
  const meta = useMeta();
  const companies = useCompanies();
  const entityRows = useMemo(() => {
    const names = new Map((companies.data?.companies ?? []).map((c) => [c.company_id, c.company_name]));
    return (sentiment.data?.by_entity ?? []).map((r) => ({ ...r, name: names.get(r.matched_company_id) ?? humanize(r.matched_company_id) }));
  }, [companies.data, sentiment.data]);

  const setParam = (key: string, value: string) =>
    setParams((p) => { if (value) p.set(key, value); else p.delete(key); return p; }, { replace: true });

  const charts = useMemo(() => {
    const d = sentiment.data;
    if (!d) return null;
    return {
      distribution: distributionOption(d),
      daily: timeSeries([{ name: "Mean sentiment", points: d.daily.map((r) => [r.date, r.mean_sentiment]), color: "#4262ff" }],
        { yFormat: numFmt(2), zeroLine: true, legend: false, zoom: d.daily.length > 60 }),
    };
  }, [sentiment.data]);

  const d = sentiment.data;
  const unscored = meta.data ? meta.data.news_count - meta.data.scored_articles : 0;
  const gate = d?.coverage?.training_gate;

  return (
    <>
      <PageHeader
        title="Sentiment"
        description="Headline sentiment from lexicon models (VADER, TextBlob), and how much of each model split the news actually covers."
        actions={d && d.models.length > 1 && (
          <PillTabs label="Sentiment model" value={d.model ?? ""} onChange={(m) => setParam("model", m)}
            options={d.models.map((m) => ({ value: m, label: m === "vader" ? "VADER" : humanize(m) }))} />
        )}
      />

      {unscored > 0 && (
        <div className="mb-6 flex items-start gap-3 rounded-2xl bg-surface-yellow p-4 text-[14px] text-yellow-dark">
          <Info className="mt-0.5 size-4 shrink-0" aria-hidden />
          <p>
            <b>{compact(unscored)} collected articles are not scored yet.</b> Scores below cover{" "}
            {compact(meta.data?.scored_articles)} articles.
            {meta.data?.pipeline_enabled && <> Run <Link to="/pipeline" className="font-semibold underline">sentiment scoring</Link> to include them.</>}
          </p>
        </div>
      )}

      <div className="mb-6 grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
        <StatCard tone="yellow" label="Scored articles" value={compact(d?.n_scored)} hint={d?.model ? `model: ${d.model}` : undefined} />
        <StatCard tone="teal" label="Training coverage" value={pct(d?.coverage?.totals.train.pct, 0)} hint="trading days with news" />
        <StatCard tone="lavender" label="Validation coverage" value={pct(d?.coverage?.totals.validation.pct, 0)} />
        <StatCard tone={gate?.met ? "teal" : "coral"} label="Ablation gate" value={gate ? (gate.met ? "Met" : "Not met") : "—"}
          hint={gate ? `needs ${pct(gate.threshold, 0)} training coverage` : undefined} />
      </div>

      <Card className="mb-6" title="Filter by label" subtitle="Applies to every chart and table below">
        <FilterPills label="Sentiment label" options={d?.labels ?? []} selected={labels} onChange={(s) => setParam("labels", s.join("|"))} />
      </Card>

      <QueryState query={sentiment} skeleton="h-[500px]">
        {(data) => (
          <>
            <div className="mb-6 grid grid-cols-1 gap-6 xl:grid-cols-5">
              <Card title="Label distribution" className="xl:col-span-2">
                <Chart option={charts!.distribution} height={280} ariaLabel="Number of articles per sentiment label" />
              </Card>
              <Card title="Daily mean sentiment" subtitle="Average score of articles published each day" className="xl:col-span-3">
                <Chart option={charts!.daily} height={280} ariaLabel="Daily mean sentiment score over time" />
              </Card>
            </div>
            <div className="grid grid-cols-1 gap-6 xl:grid-cols-5">
              <Card title="By company" subtitle="Companies matched in scored headlines" className="xl:col-span-3">
                <DataTable data={entityRows} columns={entityColumns} dense initialSort={[{ id: "n_articles", desc: true }]} caption="Sentiment by company" />
              </Card>
              <Card title="News coverage by split" subtitle="Share of trading days with at least one article (all collected news)" className="xl:col-span-2">
                {data.coverage ? <CoverageTable coverage={data.coverage} /> : <p className="text-steel">Run the news backfill to compute coverage.</p>}
              </Card>
            </div>
          </>
        )}
      </QueryState>
    </>
  );
}
