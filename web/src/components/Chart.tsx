import { BarChart, HeatmapChart, LineChart, ScatterChart } from "echarts/charts";
import {
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TooltipComponent,
  VisualMapComponent,
} from "echarts/components";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { useEffect, useRef } from "react";

import { darken, PALETTE } from "../lib/chartTheme";
import { useTheme } from "../lib/theme";

echarts.use([
  LineChart, BarChart, HeatmapChart, ScatterChart,
  GridComponent, TooltipComponent, LegendComponent, DataZoomComponent, VisualMapComponent, MarkLineComponent,
  CanvasRenderer,
]);

export type ChartOption = echarts.EChartsCoreOption;

/** Thin ECharts wrapper: tree-shaken core, resizes with its container. */
export function Chart({ option, height = 320, ariaLabel }: { option: ChartOption; height?: number; ariaLabel: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const chart = useRef<echarts.ECharts | null>(null);
  const { theme } = useTheme();

  useEffect(() => {
    if (!ref.current) return;
    const instance = echarts.init(ref.current, undefined, { renderer: "canvas" });
    chart.current = instance;
    const observer = new ResizeObserver(() => instance.resize());
    observer.observe(ref.current);
    return () => {
      observer.disconnect();
      instance.dispose();
      chart.current = null;
    };
  }, []);

  useEffect(() => {
    const full = { color: PALETTE, textStyle: { fontFamily: "Figtree, sans-serif" }, animationDuration: 300, ...option };
    chart.current?.setOption(theme === "dark" ? darken(full) : full, { notMerge: true });
  }, [option, theme]);

  return <div ref={ref} role="img" aria-label={ariaLabel} style={{ height, width: "100%" }} />;
}
