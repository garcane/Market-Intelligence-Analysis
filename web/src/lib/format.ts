import type { Num } from "../api/types";

const DASH = "—";

export function pct(value: Num | undefined, digits = 1, signed = false): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return DASH;
  const text = `${(value * 100).toFixed(digits)}%`;
  return signed && value > 0 ? `+${text}` : text;
}

export function num(value: Num | undefined, digits = 2): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return DASH;
  return value.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export function compact(value: Num | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return DASH;
  return new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

export function price(value: Num | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return DASH;
  const digits = Math.abs(value) >= 1000 ? 0 : 2;
  return value.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export function shortDate(iso: string | null | undefined): string {
  if (!iso) return DASH;
  const d = new Date(iso.length === 10 ? `${iso}T00:00:00` : iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

export function relativeTime(iso: string | null | undefined, now = new Date()): string {
  if (!iso) return DASH;
  const then = new Date(iso);
  const minutes = Math.round((now.getTime() - then.getTime()) / 60000);
  if (!Number.isFinite(minutes)) return iso;
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 48) return `${hours}h ago`;
  return shortDate(iso);
}

/** "hist_gradient_boosting" -> "Hist gradient boosting"; known acronyms kept. */
export function humanize(key: string): string {
  const words = key.replace(/_/g, " ").trim();
  const text = words.charAt(0).toUpperCase() + words.slice(1);
  return text
    .replace(/\bai\b/gi, "AI")
    .replace(/\bauc\b/gi, "AUC")
    .replace(/\bpr\b/gi, "PR")
    .replace(/\broc\b/gi, "ROC")
    .replace(/\bxgboost\b/gi, "XGBoost")
    .replace(/\bspx\b/gi, "SPX")
    .replace(/\brsi\b/gi, "RSI");
}

export function signClass(value: Num | undefined): string {
  if (value === null || value === undefined || value === 0) return "text-slate";
  return value > 0 ? "text-gain" : "text-loss";
}
