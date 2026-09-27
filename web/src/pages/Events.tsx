import clsx from "clsx";
import { Search } from "lucide-react";
import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import { useEvents } from "../api/client";
import { Chart, type ChartOption } from "../components/Chart";
import { Badge, type BadgeTone, Card, Delta, FilterPills, PageHeader, PillTabs, QueryState, StatCard } from "../components/ui";
import { AXIS, GAIN, LOSS, TOOLTIP } from "../lib/chartTheme";
import { humanize, shortDate } from "../lib/format";
import type { EventRow, Events as EventsData } from "../api/types";

const TYPE_TONE: Record<string, BadgeTone> = {
  model_release: "blue", partnership: "teal", investment: "gain", acquisition: "coral",
  hardware: "yellow", infrastructure: "dark", earnings: "neutral", market_reaction: "loss",
};

const ACRONYMS: Record<string, string> = { ipo: "IPO" };
const typeLabel = (t: string) => ACRONYMS[t] ?? humanize(t);

type Source = "all" | "curated" | "news";
const splitParam = (v: string | null) => (v ? v.split("|").filter(Boolean) : []);

function matches(e: EventRow, types: string[], source: Source, needle: string) {
  return (!types.length || types.includes(typeLabel(e.event_type))) &&
    (source === "all" || e.source === source) &&
    (!needle || `${e.title} ${e.description} ${e.organisation ?? ""} ${e.primary_market_id ?? ""}`.toLowerCase().includes(needle));
}

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

function noReactionReason(e: EventRow): string {
  if (e.source === "news") return "Detected from news; price reactions are measured for curated events only.";
  if (!e.primary_market_id) return "No listed company to measure a price reaction against.";
  return "No price window available for this event.";
}

export default function Events() {
  const events = useEvents();
  const [params, setParams] = useSearchParams();
  const types = splitParam(params.get("type"));
  const sourceParam = params.get("source");
  const source: Source = sourceParam === "curated" || sourceParam === "news" ? sourceParam : "all";
  const q = params.get("q") ?? "";
  const update = (key: string, value: string) =>
    setParams((p) => { if (value) p.set(key, value); else p.delete(key); return p; }, { replace: true });

  const view = useMemo(() => {
    const d = events.data;
    if (!d) return null;
    const outcomes = new Map(d.outcomes.map((o) => [o.event_id, o]));
    // newest first: the timeline reads from the latest developments back
    const all = [...d.events].sort((a, b) => b.event_date.localeCompare(a.event_date));
    return {
      outcomes,
      all,
      typeOptions: [...new Set(all.map((e) => typeLabel(e.event_type)))].sort(),
      orgs: new Set(all.map((e) => e.organisation).filter(Boolean)).size,
      models: all.filter((e) => e.event_type === "model_release").length,
      detected: all.filter((e) => e.source === "news").length,
      caar: d.caar.length ? caarOption(d) : null,
    };
  }, [events.data]);

  const needle = q.trim().toLowerCase();
  const typeKey = types.join("|");
  const list = useMemo(
    () => (view?.all ?? []).filter((e) => matches(e, splitParam(typeKey), source, needle)),
    [view, typeKey, source, needle],
  );
  const byYear = useMemo(() => {
    const groups = new Map<string, EventRow[]>();
    for (const e of list) {
      const year = e.event_date.slice(0, 4);
      groups.set(year, [...(groups.get(year) ?? []), e]);
    }
    return [...groups.entries()];
  }, [list]);

  const selectedId = params.get("event")
    ?? list.find((e) => view?.outcomes.get(e.event_id)?.status === "OK")?.event_id
    ?? list[0]?.event_id;
  const selected = view?.all.find((e) => e.event_id === selectedId);
  const outcome = selectedId ? view?.outcomes.get(selectedId) : undefined;
  const windowPoints = selectedId ? events.data?.abnormal_returns[selectedId] : undefined;
  const eventChart = useMemo(() => (windowPoints ? eventOption(windowPoints) : null), [windowPoints]);

  return (
    <>
      <PageHeader
        title="AI events"
        description="Model releases, deals, chips and data-centre build-outs across the AI landscape, and how prices reacted. Curated events are checked by hand; the rest are detected automatically from news headlines. Abnormal return is the asset's return minus the benchmark's on the same day."
      />
      <QueryState query={events} skeleton="h-[600px]">
        {(d) => (
          <>
            <div className="mb-6 grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
              <StatCard tone="yellow" label="Events" value={view!.all.length}
                hint={`${shortDate(view!.all.at(-1)?.event_date)} – ${shortDate(view!.all[0]?.event_date)}`} />
              <StatCard tone="teal" label="Model releases" value={view!.models} />
              <StatCard tone="coral" label="Organisations" value={view!.orgs} />
              <StatCard tone="rose" label="Detected from news" value={view!.detected} hint="found automatically in headlines" />
            </div>

            {view!.caar && (
              <Card
                title="Average reaction across events"
                subtitle={`${d.caar[0]?.n_events ?? 0} curated events with a listed company, ±${d.window} trading days, benchmark ${d.benchmark}`}
                className="mb-6"
              >
                <Chart option={view!.caar} height={300} ariaLabel="Average and cumulative abnormal returns around AI events" />
              </Card>
            )}

            <Card className="mb-6">
              <div className="flex flex-col gap-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <PillTabs<Source>
                    label="Source"
                    value={source}
                    onChange={(v) => update("source", v === "all" ? "" : v)}
                    options={[{ value: "all", label: "All" }, { value: "curated", label: "Curated" }, { value: "news", label: "From news" }]}
                  />
                  <label className="relative block w-full sm:w-64">
                    <span className="sr-only">Search events</span>
                    <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-stone" aria-hidden />
                    <input
                      value={q}
                      onChange={(e) => update("q", e.target.value)}
                      placeholder="Search, e.g. Claude or Nvidia"
                      className="h-10 w-full rounded-lg border border-hairline bg-surface pr-3 pl-9 text-[14px] placeholder:text-muted"
                    />
                  </label>
                </div>
                <FilterPills label="Event type" options={view!.typeOptions} selected={types} onChange={(s) => update("type", s.join("|"))} />
              </div>
            </Card>

            <div className="grid grid-cols-1 gap-6 xl:grid-cols-5">
              <Card title={`Timeline · ${list.length} events`} className="xl:col-span-2" bodyClassName="p-3">
                <div className="max-h-[720px] overflow-y-auto pr-1">
                  {byYear.map(([year, items]) => (
                    <section key={year} aria-label={year}>
                      <h3 className="sticky top-0 z-10 bg-canvas px-3 pt-2 pb-1 text-[12px] font-semibold tracking-[0.5px] text-stone uppercase">
                        {year}
                      </h3>
                      <ol className="flex flex-col gap-1">
                        {items.map((e) => {
                          const car = view!.outcomes.get(e.event_id)?.cumulative_abnormal_return_full_window;
                          const active = e.event_id === selectedId;
                          return (
                            <li key={e.event_id}>
                              <button
                                onClick={() => update("event", e.event_id)}
                                aria-current={active}
                                className={clsx("flex w-full items-start gap-3 rounded-xl p-3 text-left transition-colors",
                                  active ? "bg-ink text-canvas" : "hover:bg-surface")}
                              >
                                <span className={clsx("tabular w-20 shrink-0 text-[12px] font-medium", active ? "text-canvas/70" : "text-steel")}>
                                  {shortDate(e.event_date)}
                                </span>
                                <span className="min-w-0 flex-1">
                                  <span className="block text-[14px] font-medium">{e.title}</span>
                                  <span className={clsx("text-[12px]", active ? "text-canvas/70" : "text-steel")}>
                                    {[typeLabel(e.event_type), e.primary_market_id, e.source === "news" ? "from news" : null].filter(Boolean).join(" · ")}
                                  </span>
                                </span>
                                {typeof car === "number" && (
                                  <span className={clsx("tabular text-[13px] font-semibold",
                                    active ? "text-canvas" : car >= 0 ? "text-gain" : "text-loss")}>
                                    {(car * 100).toFixed(1)}%
                                  </span>
                                )}
                              </button>
                            </li>
                          );
                        })}
                      </ol>
                    </section>
                  ))}
                  {!list.length && <p className="p-3 text-[14px] text-steel">No events match these filters.</p>}
                </div>
              </Card>

              <Card
                className="xl:col-span-3"
                title={selected?.title ?? "Select an event"}
                subtitle={selected ? [shortDate(selected.event_date), selected.primary_market_id].filter(Boolean).join(" · ") : undefined}
                action={selected && (
                  <div className="flex flex-wrap gap-1.5">
                    <Badge tone={TYPE_TONE[selected.event_type] ?? "neutral"}>{typeLabel(selected.event_type)}</Badge>
                    <Badge tone={selected.source === "news" ? "coral" : "gain"}>{selected.source === "news" ? "from news" : "curated"}</Badge>
                  </div>
                )}
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
                          <Chart option={eventChart} height={260} ariaLabel={`Daily abnormal returns around ${selected.title}`} />
                        )}
                      </>
                    ) : (
                      <p className="text-[14px] text-steel">{noReactionReason(selected)}</p>
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
