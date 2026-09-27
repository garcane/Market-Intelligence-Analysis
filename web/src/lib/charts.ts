import type { ChartOption } from "../components/Chart";
import { AXIS, GAIN, LOSS, PALETTE, TOOLTIP } from "./chartTheme";

type Formatter = (value: number) => string;

export const pctFmt = (digits = 0): Formatter => (v) => `${(v * 100).toFixed(digits)}%`;
export const numFmt = (digits = 2): Formatter => (v) =>
  v.toLocaleString("en-US", { maximumFractionDigits: digits });

export interface LineSeries {
  name: string;
  points: [string, number | null][];
  color?: string;
  area?: boolean;
}

/** Time-series lines on a date axis, optionally with a zoom slider. */
export function timeSeries(series: LineSeries[], opts: {
  yFormat?: Formatter;
  zoom?: boolean;
  legend?: boolean;
  zeroLine?: boolean;
  yMin?: number | "dataMin";
} = {}): ChartOption {
  const fmt = opts.yFormat ?? numFmt();
  const legend = opts.legend ?? series.length > 1;
  return {
    grid: { left: 8, right: 16, top: legend ? 40 : 16, bottom: opts.zoom ? 64 : 8, containLabel: true },
    legend: legend ? { top: 0, left: 0, icon: "roundRect", itemWidth: 12, itemHeight: 4, textStyle: { color: "#555a6a" } } : undefined,
    tooltip: {
      ...TOOLTIP,
      valueFormatter: (v: unknown) => (typeof v === "number" ? fmt(v) : "—"),
    },
    xAxis: { type: "time", ...AXIS, splitLine: { show: false } },
    yAxis: { type: "value", scale: true, min: opts.yMin, ...AXIS, axisLabel: { ...AXIS.axisLabel, formatter: fmt } },
    dataZoom: opts.zoom
      ? [
          { type: "inside", throttle: 50 },
          { type: "slider", height: 28, bottom: 12, borderColor: "#e0e2e8", fillerColor: "rgba(66,98,255,0.08)",
            handleStyle: { color: "#1c1c1e" }, textStyle: { color: "#6b6f7e" } },
        ]
      : undefined,
    series: series.map((s) => ({
      name: s.name,
      type: "line",
      showSymbol: false,
      sampling: "lttb",
      lineStyle: { width: 1.75 },
      color: s.color,
      areaStyle: s.area ? { opacity: 0.12 } : undefined,
      data: s.points,
      markLine: opts.zeroLine
        ? { silent: true, symbol: "none", label: { show: false }, lineStyle: { color: "#c7cad5", type: "dashed" }, data: [{ yAxis: 0 }] }
        : undefined,
    })),
  };
}

/** Horizontal bars, largest at the top. Values below zero are drawn red when `signed`. */
export function horizontalBars(rows: { label: string; value: number | null; error?: number | null }[], opts: {
  format?: Formatter;
  color?: string;
  signed?: boolean;
  reference?: { value: number; label: string };
} = {}): ChartOption {
  const fmt = opts.format ?? numFmt(3);
  const data = [...rows].reverse();
  return {
    grid: { left: 8, right: 56, top: opts.reference ? 28 : 8, bottom: 8, containLabel: true },
    tooltip: { ...TOOLTIP, trigger: "axis", axisPointer: { type: "shadow" }, valueFormatter: (v: unknown) => (typeof v === "number" ? fmt(v) : "—") },
    // values are labelled on the bars, so the value axis only adds clutter
    xAxis: { type: "value", ...AXIS, axisLabel: { show: false }, splitLine: { show: false } },
    yAxis: { type: "category", data: data.map((r) => r.label), ...AXIS, axisLabel: { ...AXIS.axisLabel, color: "#2c2c34" } },
    series: [{
      type: "bar",
      barMaxWidth: 18,
      data: data.map((r) => ({
        value: r.value,
        itemStyle: {
          color: opts.signed && (r.value ?? 0) < 0 ? LOSS : opts.signed ? GAIN : (opts.color ?? "#4262ff"),
          borderRadius: (r.value ?? 0) < 0 ? [4, 0, 0, 4] : [0, 4, 4, 0],
        },
      })),
      label: { show: true, position: "right", color: "#555a6a", fontSize: 12, formatter: (p: { value: number }) => fmt(p.value) },
      markLine: opts.reference
        ? { silent: true, symbol: "none", lineStyle: { color: "#1c1c1e", type: "dashed" },
            label: { formatter: opts.reference.label, position: "end", color: "#1c1c1e", fontSize: 11 }, data: [{ xAxis: opts.reference.value }] }
        : undefined,
    }],
  };
}

/** Symmetric correlation heatmap, -1 (red) to +1 (blue). */
export function correlationHeatmap(ids: string[], matrix: (number | null)[][]): ChartOption {
  const data: [number, number, number | null][] = [];
  matrix.forEach((row, i) => row.forEach((v, j) => data.push([j, i, v === null ? null : Number(v.toFixed(2))])));
  return {
    grid: { left: 8, right: 8, top: 8, bottom: 56, containLabel: true },
    tooltip: {
      ...TOOLTIP,
      trigger: "item",
      formatter: (p: { data: [number, number, number | null] }) =>
        `${ids[p.data[1]]} × ${ids[p.data[0]]}<br/><b>${p.data[2] ?? "—"}</b>`,
    },
    xAxis: { type: "category", data: ids, ...AXIS, axisLabel: { ...AXIS.axisLabel, rotate: 45 }, splitArea: { show: false } },
    yAxis: { type: "category", data: ids, ...AXIS, inverse: true },
    visualMap: {
      min: -1, max: 1, calculable: false, text: ["+1", "−1"], orient: "horizontal", left: "center", bottom: 0, itemHeight: 160, itemWidth: 10,
      inRange: { color: ["#e5484d", "#ffc6c6", "#ffffff", "#c9d3ff", "#4262ff"] }, textStyle: { color: "#6b6f7e" },
    },
    series: [{
      type: "heatmap",
      data,
      label: { show: ids.length <= 12, fontSize: 10, color: "#1c1c1e" },
      itemStyle: { borderColor: "#ffffff", borderWidth: 1 },
      emphasis: { itemStyle: { borderColor: "#1c1c1e" } },
    }],
  };
}

export interface CurveSeries {
  name: string;
  /** [x, y, threshold] */
  points: [number, number, number][];
  /** the operating point at the selected threshold */
  marker?: [number, number, number];
}

/** Classifier curves on the unit square (ROC, precision-recall): legend
 * toggling, zoom, a dashed reference line and a marker per model at the
 * selected threshold. */
export function xyCurves(series: CurveSeries[], opts: {
  xName: string;
  yName: string;
  reference: { label: string; points: [number, number][] };
}): ChartOption {
  const fmt = numFmt(3);
  return {
    grid: { left: 44, right: 24, top: 40, bottom: 44, containLabel: true },
    legend: { top: 0, left: 0, icon: "roundRect", itemWidth: 12, itemHeight: 4, textStyle: { color: "#555a6a" } },
    tooltip: {
      ...TOOLTIP,
      trigger: "item",
      formatter: (p: { seriesName: string; data: number[]; marker: string }) => {
        const [x, y, t] = p.data;
        const threshold = t === undefined ? "" : `<br/>threshold ${fmt(t)}`;
        return `${p.marker}<b>${p.seriesName}</b><br/>${opts.xName} ${fmt(x)} · ${opts.yName} ${fmt(y)}${threshold}`;
      },
    },
    xAxis: { type: "value", min: 0, max: 1, name: opts.xName, nameLocation: "middle", nameGap: 28, ...AXIS,
      nameTextStyle: { color: "#6b6f7e" } },
    yAxis: { type: "value", min: 0, max: 1, name: opts.yName, nameLocation: "middle", nameGap: 40, ...AXIS,
      nameTextStyle: { color: "#6b6f7e" } },
    dataZoom: [{ type: "inside", xAxisIndex: 0, filterMode: "none" }, { type: "inside", yAxisIndex: 0, filterMode: "none" }],
    series: [
      ...series.map((s, i) => ({
        name: s.name,
        type: "line",
        showSymbol: false,
        color: PALETTE[i % PALETTE.length],
        lineStyle: { width: 1.75 },
        emphasis: { focus: "series" },
        data: s.points,
      })),
      // same name as the line, so toggling a legend item hides both
      ...series.flatMap((s, i) => s.marker ? [{
        name: s.name,
        type: "scatter",
        symbolSize: 11,
        z: 5,
        itemStyle: { color: PALETTE[i % PALETTE.length], borderColor: "#ffffff", borderWidth: 2 },
        data: [s.marker],
      }] : []),
      {
        name: opts.reference.label,
        type: "line",
        showSymbol: false,
        silent: true,
        lineStyle: { type: "dashed", width: 1.25, color: "#c7cad5" },
        itemStyle: { color: "#c7cad5" },
        data: opts.reference.points,
      },
    ],
  };
}
