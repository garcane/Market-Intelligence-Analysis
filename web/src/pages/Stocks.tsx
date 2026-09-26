import { useMemo } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";

import { useMarkets, usePrices } from "../api/client";
import { Chart } from "../components/Chart";
import { Badge, Card, Delta, PageHeader, PillTabs, QueryState, Select, StatCard } from "../components/ui";
import { GAIN, LOSS } from "../lib/chartTheme";
import { numFmt, pctFmt, timeSeries } from "../lib/charts";
import { pct, price, shortDate } from "../lib/format";

const RANGES = ["1M", "3M", "6M", "1Y", "YTD", "ALL"] as const;
type Range = (typeof RANGES)[number];

function rangeStart(range: Range, end: string): string | undefined {
  const d = new Date(`${end}T00:00:00`);
  if (range === "ALL") return undefined;
  if (range === "YTD") return `${d.getFullYear()}-01-01`;
  const months = { "1M": 1, "3M": 3, "6M": 6, "1Y": 12 }[range];
  d.setMonth(d.getMonth() - months);
  return d.toISOString().slice(0, 10);
}

export default function Stocks() {
  const { id = "NVDA" } = useParams();
  const navigate = useNavigate();
  const [search, setSearch] = useSearchParams();
  const range = (RANGES.includes(search.get("range") as Range) ? search.get("range") : "1Y") as Range;

  const markets = useMarkets();
  const market = markets.data?.find((m) => m.market_id === id);
  const start = market ? rangeStart(range, market.end_date) : undefined;
  const prices = usePrices(market ? id : undefined, start);

  const charts = useMemo(() => {
    const rows = prices.data?.rows ?? [];
    const up = (rows.at(-1)?.close ?? 0) >= (rows[0]?.close ?? 0);
    return {
      price: timeSeries([{ name: id, points: rows.map((r) => [r.date, r.close]), color: up ? GAIN : LOSS, area: true }],
        { yFormat: numFmt(2), zoom: true, legend: false }),
      cumulative: timeSeries([{ name: "Cumulative return", points: rows.map((r) => [r.date, r.cumulative_return]), color: "#4262ff" }],
        { yFormat: pctFmt(0), legend: false, zeroLine: true }),
      drawdown: timeSeries([{ name: "Drawdown", points: rows.map((r) => [r.date, r.drawdown]), color: LOSS, area: true }],
        { yFormat: pctFmt(0), legend: false }),
    };
  }, [prices.data, id]);

  const options = (markets.data ?? [])
    .map((m) => ({ value: m.market_id, label: `${m.market_id} · ${m.kind}` }))
    .sort((a, b) => a.value.localeCompare(b.value));

  const s = prices.data?.summary;

  return (
    <>
      <PageHeader
        title={`${id} performance`}
        description="Price, cumulative return and drawdown over the selected range. Drag the slider under the price chart to zoom."
        actions={
          <Select
            label="Asset"
            value={id}
            onChange={(v) => navigate({ pathname: `/stocks/${v}`, search: search.toString() })}
            options={options.length ? options : [{ value: id, label: id }]}
            className="w-52"
          />
        }
      />

      {markets.data && !market ? (
        <Card><p className="text-slate">No price data for <b>{id}</b>. Pick another asset above.</p></Card>
      ) : (
        <>
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <PillTabs<Range>
              label="Date range"
              value={range}
              onChange={(r) => setSearch((p) => { p.set("range", r); return p; }, { replace: true })}
              options={RANGES.map((r) => ({ value: r, label: r === "ALL" ? "All" : r }))}
            />
            {prices.data && (
              <div className="flex flex-wrap items-center gap-2 text-[13px] text-steel">
                {shortDate(prices.data.rows[0]?.date)} – {shortDate(prices.data.rows.at(-1)?.date)}
                {prices.data.sources.map((src) => <Badge key={src}>{src.replace("_", " ")}</Badge>)}
              </div>
            )}
          </div>

          <div className="mb-6 grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
            <StatCard tone="yellow" label="Last close" value={price(prices.data?.rows.at(-1)?.close)}
              hint={<Delta value={prices.data?.rows.at(-1)?.return_1d ?? null} digits={2} />} />
            <StatCard tone="teal" label="Return over range" value={pct(s?.total_return, 1, true)} />
            <StatCard tone="lavender" label="Annualised volatility" value={pct(s?.annualized_volatility)} />
            <StatCard tone="coral" label="Max drawdown" value={pct(s?.max_drawdown)} />
          </div>

          <Card title="Close price" className="mb-6">
            <QueryState query={prices} skeleton="h-[380px]">
              {() => <Chart option={charts.price} height={380} ariaLabel={`${id} close price over time`} />}
            </QueryState>
          </Card>

          <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
            <Card title="Cumulative return" subtitle="Rebased to the start of the range">
              <QueryState query={prices}>
                {() => <Chart option={charts.cumulative} height={260} ariaLabel={`${id} cumulative return`} />}
              </QueryState>
            </Card>
            <Card title="Drawdown" subtitle="Distance below the running peak">
              <QueryState query={prices}>
                {() => <Chart option={charts.drawdown} height={260} ariaLabel={`${id} drawdown from peak`} />}
              </QueryState>
            </Card>
          </div>
        </>
      )}
    </>
  );
}
