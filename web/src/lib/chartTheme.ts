// Muted categorical palette derived from the pastel tokens, saturated enough for lines.
export const PALETTE = ["#4262ff", "#0fbcb0", "#f08a4b", "#e5484d", "#8b5cf6", "#187574", "#fcb900", "#6b6f7e"];

export const AXIS = {
  axisLine: { lineStyle: { color: "#e0e2e8" } },
  axisTick: { show: false },
  axisLabel: { color: "#6b6f7e", fontSize: 12 },
  splitLine: { lineStyle: { color: "#eef0f3" } },
};

export const TOOLTIP = {
  trigger: "axis" as const,
  backgroundColor: "#ffffff",
  borderColor: "#e0e2e8",
  textStyle: { color: "#1c1c1e", fontSize: 13 },
  extraCssText: "border-radius:12px;box-shadow:0 16px 48px -8px rgba(5,0,56,.12);",
};

export const GAIN = "#00b473";
export const LOSS = "#e5484d";

// Dark-theme stand-ins for the neutral colours the option builders hard-code
// (axes, split lines, legends, tooltips, reference lines, heatmap midpoints).
// Chart.tsx swaps them in when the dark theme is on; series colours stay.
export const DARK_COLORS: Record<string, string> = {
  "#ffffff": "#1d1f26",
  "#e0e2e8": "#3a3e4b",
  "#eef0f3": "#262933",
  "#c7cad5": "#5a5f6e",
  "#6b6f7e": "#9a9eab",
  "#555a6a": "#b4b8c4",
  "#2c2c34": "#d6d8e0",
  "#1c1c1e": "#eceef3",
  "#ffc6c6": "#7a3436",
  "#c9d3ff": "#34407a",
};

/** Deep copy of an option with neutral colours swapped for their dark variants. */
export function darken<T>(value: T): T {
  if (typeof value === "string") return (DARK_COLORS[value.toLowerCase()] ?? value) as T;
  if (Array.isArray(value)) return value.map(darken) as T;
  if (value && typeof value === "object" && Object.getPrototypeOf(value) === Object.prototype) {
    return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, darken(v)])) as T;
  }
  return value;
}
