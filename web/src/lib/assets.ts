import type { AssetKind, MarketRow } from "../api/types";
import type { BadgeTone } from "../components/ui";

/** Top-level asset categories, in display order. "All" shows everything. */
export const CATEGORIES = ["All", "Stocks", "AI Supply Chain", "Energy", "Benchmarks", "Crypto"] as const;
export type Category = (typeof CATEGORIES)[number];

export const KIND_LABEL: Record<AssetKind, string> = { stock: "Stock", etf: "ETF", index: "Index", crypto: "Crypto" };
export const KIND_TONE: Record<AssetKind, BadgeTone> = { stock: "blue", etf: "teal", index: "neutral", crypto: "yellow" };

export const inCategory = (m: Pick<MarketRow, "categories">, c: Category) => c === "All" || m.categories.includes(c);

export const asCategory = (v: string | null): Category =>
  (CATEGORIES as readonly string[]).includes(v ?? "") ? (v as Category) : "All";

/** Currency suffix for non-USD prices, e.g. "GBp" for pence-quoted London ETFs. */
export const currencySuffix = (currency: string | null | undefined) =>
  currency && currency !== "USD" ? ` ${currency}` : "";
