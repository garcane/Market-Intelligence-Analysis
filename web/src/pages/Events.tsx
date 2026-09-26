import clsx from "clsx";
import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import { useEvents } from "../api/client";
import { Chart, type ChartOption } from "../components/Chart";
import { Badge, Card, Delta, PageHeader, QueryState } from "../components/ui";
import { AXIS, GAIN, LOSS, TOOLTIP } from "../lib/chartTheme";
import { humanize, shortDate } from "../lib/format";
import type { Events as EventsData } from "../api/types";

function caarOption(d: EventsData): ChartOption {
  const days = d.caar.map((r) => (r.day > 0 ? `+${r.day}` : String(r.day)));
  const fmt = (v: number) => `${(v * 100).toFixed(1)}%`;
  return {
    grid: { left: 8, right: 16, top: 40, bottom: 8, containLabel: true },
    legend: { top: 0, left: 0, textStyle: { color: "#555a6a" } },
    tooltip: { ...TOOLTIP, valueFormatter: (v: unknown) => (typeof v === "number" ? fmt(v) : "—") },
    xAxis: { type: "category", data: days, name: "Trading day vs event", nameLocation: "middle", nameGap: 28, ...AXIS },
    yAxis: { type: "value", ...AXIS, axisLabel: { ...AXIS.axisLabel, formatter: fmt } },
    series: [
      { name: "Average abnormal return", type: "bar", barMaxWidth: 22,
        data: d.caar.map((r) => ({ value: r.AAR, itemStyle: { color: (r.AAR ?? 0) >= 0 ? GAIN : LOSS, borderRadius: 4 } })) },
      { name: "Cumulative (CAAR)", type: "line", data: d.caar.map((r) => r.CAAR), color: "#1c1c1e", symbolSize: 6, lineStyle: { width: 2 },
        markLine: { silent: true, symbol: "none", label: { show: false }, lineStyle: { color: "#c7cad5", type: "dashed" }, data: [{ xAxis: "0" }] } },
    ],
  };
}

function eventOption(points: { day: number; value: number }[]): ChartOption {
  const fmt = (v: number) => `${(v * 100).toFixed(1)}%`;
  let running = 0;
  return {
    grid: { left: 8, right: 16, top: 40, bottom: 8, containLabel: true },
    legend: { top: 0, left: 0, textStyle: { color: "#555a6a" } },
    tooltip: { ...TOOLTIP, valueFormatter: (v: unknown) => (typeof v === "number" ? fmt(v) : "—") },
    xAxis: { type: "category", data: points.map((p) => (p.day > 0 ? `+${p.day}` : String(p.day))), ...AXIS },
    yAxis: { type: "value", ...AXIS, axisLabel: { ...AXIS.axisLabel, formatter: fmt } },
    series: [
      { name: "Abnormal return", type: "bar", barMaxWidth: 22,
        data: points.map((p) => ({ value: p.value, itemStyle: { color: p.value >= 0 ? GAIN : LOSS, borderRadius: 4 } })) },
      { name: "Cumulative", type: "line", color: "#1c1c1e", symbolSize: 6, lineStyle: { width: 2 },
        data: points.map((p) => (running += p.value)),
        markLine: { silent: true, symbol: "none", label: { show: false }, lineStyle: { color: "#c7cad5", type: "dashed" }, data: [{ xAxis: "0" }] } },
    ],
  };
}

export default function Events() {
  const events = useEvents();
  const [params, setParams] = useSearchParams();

  const view = useMemo(() => {
    const d = events.data;
    if (!d) return null;
    const outcomes = new Map(d.outcomes.map((o) => [o.event_id, o]));
    const list = [...d.events].sort((a, b) => a.event_date.localeCompare(b.event_date));
    return { outcomes, list, caar: d.caar.length ? caarOption(d) : null };
  }, [events.data]);

  const selectedId = params.get("event") ?? view?.list.find((e) => view.outcomes.get(e.event_id)?.status === "OK")?.event_id;
  const selected = view?.list.find((e) => e.event_id === selectedId);
  const outcome = selectedId ? view?.outcomes.get(selectedId) : undefined;
  const windowPoints = selectedId ? events.data?.abnormal_returns[selectedId] : undefined;
  const eventChart = useMemo(() => (windowPoints ? eventOption(windowPoints) : null), [windowPoints]);

  return (
    <>
      <PageHeader
        title="AI events"
        description="How prices reacted around major AI moments. Abnormal return is the asset's return minus the benchmark's on the same day."
      />
      <QueryState query={events} skeleton="h-[600px]">
        {(d) => (
          <>
            {view!.caar && (
              <Card
                title="Average reaction across events"
                subtitle={`${d.caar[0]?.n_events ?? 0} events, ±${d.window} trading days, benchmark ${d.benchmark}`}
                className="mb-6"
              >
                <Chart option={view!.caar} height={300} ariaLabel="Average and cumulative abnormal returns around AI events" />
              </Card>
            )}

            <div className="grid grid-cols-1 gap-6 xl:grid-cols-5">
              <Card title="Timeline" className="xl:col-span-2" bodyClassName="p-3">
                <ol className="flex flex-col gap-1">
                  {view!.list.map((e) => {
                    const o = view!.outcomes.get(e.event_id);
                    const active = e.event_id === selectedId;
                    return (
                      <li key={e.event_id}>
                        <button
                          onClick={() => setParams({ event: e.event_id }, { replace: true })}
                          aria-current={active}
                          className={clsx("flex w-full items-start gap-3 rounded-xl p-3 text-left transition-colors",
                            active ? "bg-ink text-white" : "hover:bg-surface")}
                        >
                          <span className={clsx("tabular w-20 shrink-0 text-[12px] font-medium", active ? "text-white/70" : "text-steel")}>
                            {shortDate(e.event_date)}
                          </span>
                          <span className="min-w-0 flex-1">
                            <span className="block text-[14px] font-medium">{e.title}</span>
                            <span className={clsx("text-[12px]", active ? "text-white/70" : "text-steel")}>
                              {humanize(e.event_type)} · {e.primary_market_id}
                            </span>
                          </span>
                          {o?.cumulative_abnormal_return_full_window !== undefined && (
                            <span className={clsx("tabular text-[13px] font-semibold", active ? "text-white" :
                              (o.cumulative_abnormal_return_full_window ?? 0) >= 0 ? "text-gain" : "text-loss")}>
                              {((o.cumulative_abnormal_return_full_window ?? 0) * 100).toFixed(1)}%
                            </span>
                          )}
                        </button>
                      </li>
                    );
                  })}
                </ol>
              </Card>

              <Card
                className="xl:col-span-3"
                title={selected?.title ?? "Select an event"}
                subtitle={selected ? `${shortDate(selected.event_date)} · ${selected.primary_market_id}` : undefined}
                action={outcome && <Badge tone={outcome.status === "OK" ? "gain" : "coral"}>{outcome.status}</Badge>}
              >
                {selected && (
                  <>
                    <p className="mb-5 text-[14px] leading-relaxed text-slate">{selected.description}</p>
                    {outcome && outcome.status === "OK" ? (
                      <>
                        <div className="mb-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
                          {[
                            ["Event-day return", outcome.t0_raw_return],
                            ["Event-day abnormal", outcome.t0_abnormal_return],
                            [`Cumulative abnormal (±${d.window}d)`, outcome.cumulative_abnormal_return_full_window],
                          ].map(([label, v]) => (
                            <div key={label as string} className="rounded-2xl bg-surface p-3">
                              <div className="text-[12px] text-steel">{label as string}</div>
                              <div className="mt-1 text-[20px]"><Delta value={(v as number | null) ?? null} /></div>
                            </div>
                          ))}
                        </div>
                        {eventChart && (
                          <Chart
                            option={eventChart}
                            height={260}
                            ariaLabel={`Daily abnormal returns around ${selected.title}`}
                          />
                        )}
                      </>
                    ) : (
                      <p className="text-[14px] text-steel">No price window available for this event.</p>
                    )}
                  </>
                )}
              </Card>
            </div>
          </>
        )}
      </QueryState>
    </>
  );
}
