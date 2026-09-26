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
