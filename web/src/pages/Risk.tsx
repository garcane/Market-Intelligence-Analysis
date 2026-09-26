import { createColumnHelper } from "@tanstack/react-table";
import { useMemo } from "react";
import { useNavigate } from "react-router-dom";

import { useCorrelation, useMarkets } from "../api/client";
import type { MarketRow } from "../api/types";
import { Chart, type ChartOption } from "../components/Chart";
import { DataTable } from "../components/DataTable";
import { Card, PageHeader, QueryState } from "../components/ui";
import { AXIS, TOOLTIP } from "../lib/chartTheme";
import { correlationHeatmap } from "../lib/charts";
import { pct } from "../lib/format";

const KIND_COLOR = { equity: "#4262ff", crypto: "#fcb900", benchmark: "#6b6f7e" } as const;
const col = createColumnHelper<MarketRow & { sharpe: number | null }>();

const columns = [
  col.accessor("market_id", { header: "Asset", cell: (c) => <span className="font-semibold">{c.getValue()}</span> }),
  col.accessor("annualized_volatility", { header: "Ann. vol", cell: (c) => pct(c.getValue()), meta: { align: "right" } }),
  col.accessor("max_drawdown", { header: "Max DD", cell: (c) => <span className="text-loss">{pct(c.getValue())}</span>, meta: { align: "right" } }),
  col.accessor("sharpe", { header: "Sharpe*", cell: (c) => c.getValue()?.toFixed(2) ?? "—", meta: { align: "right" } }),
];

function riskReturn(rows: MarketRow[]): ChartOption {
  return {
    grid: { left: 8, right: 24, top: 16, bottom: 8, containLabel: true },
    tooltip: {
      ...TOOLTIP,
      trigger: "item",
      formatter: (p: { data: [number, number, string] }) =>
        `<b>${p.data[2]}</b><br/>Volatility ${(p.data[0] * 100).toFixed(1)}%<br/>Mean daily return ${(p.data[1] * 100).toFixed(3)}%`,
    },
    xAxis: { type: "value", name: "Annualised volatility", nameLocation: "middle", nameGap: 28, scale: true, ...AXIS,
      axisLabel: { ...AXIS.axisLabel, formatter: (v: number) => `${Math.round(v * 100)}%` } },
    yAxis: { type: "value", scale: true, ...AXIS,
      axisLabel: { ...AXIS.axisLabel, formatter: (v: number) => `${(v * 100).toFixed(2)}%` } },
    series: (["equity", "crypto", "benchmark"] as const).map((kind) => ({
      name: kind,
      type: "scatter",
      symbolSize: 14,
      itemStyle: { color: KIND_COLOR[kind], opacity: 0.85 },
      label: { show: true, formatter: (p: { data: [number, number, string] }) => p.data[2], position: "right", fontSize: 11, color: "#2c2c34" },
      data: rows.filter((r) => r.kind === kind).map((r) => [r.annualized_volatility, r.mean_daily_return, r.market_id]),
    })),
  };
}

export default function Risk() {
  const markets = useMarkets();
  const correlation = useCorrelation();
  const navigate = useNavigate();

  const rows = useMemo(() => (markets.data ?? []).map((m) => {
    const days = m.kind === "crypto" ? 365 : 252;
    const vol = m.annualized_volatility;
    return { ...m, sharpe: vol && m.mean_daily_return !== null ? (m.mean_daily_return * days) / vol : null };
  }), [markets.data]);
  const scatter = useMemo(() => riskReturn(markets.data ?? []), [markets.data]);
  const heatmap = useMemo(
    () => (correlation.data ? correlationHeatmap(correlation.data.ids, correlation.data.matrix) : null),
    [correlation.data],
  );

  return (
    <>
      <PageHeader
        title="Risk analytics"
        description="Volatility, drawdowns and how closely assets move together. Crypto trades every day, so its figures annualise over 365 days."
      />
      <div className="mb-6 grid grid-cols-1 gap-6 xl:grid-cols-5">
        <Card title="Risk vs return" subtitle="Annualised volatility against mean daily return, per asset over its full history" className="xl:col-span-3">
          <QueryState query={markets} skeleton="h-[560px]">
            {() => <Chart option={scatter} height={560} ariaLabel="Scatter of volatility against mean daily return per asset" />}
          </QueryState>
        </Card>
        <Card title="Risk table" subtitle="*Sharpe with a zero risk-free rate" className="xl:col-span-2">
          <QueryState query={markets}>
            {() => (
              <DataTable data={rows} columns={columns} dense initialSort={[{ id: "annualized_volatility", desc: true }]}
                onRowClick={(r) => navigate(`/stocks/${r.market_id}`)} caption="Risk by asset" />
            )}
          </QueryState>
        </Card>
      </div>
      <Card title="Return correlation" subtitle="Pearson correlation of daily returns on shared trading days">
        <QueryState query={correlation} skeleton="h-[520px]">
          {() => <Chart option={heatmap!} height={560} ariaLabel="Correlation matrix of daily returns" />}
        </QueryState>
      </Card>
    </>
  );
}
