// Response shapes of the FastAPI backend (api/routers/*). Numbers the backend
// could not compute (NaN) arrive as null.

export type Num = number | null;

export interface Meta {
  mode: "local" | "public";
  pipeline_enabled: boolean;
  market_ids: string[];
  latest_price_date: string | null;
  news_count: number;
  latest_news: string | null;
  scored_articles: number;
}

export type AssetKind = "stock" | "etf" | "index" | "crypto";

export interface SummaryStats {
  n_days: number;
  start_date: string;
  end_date: string;
  mean_daily_return: Num;
  annualized_volatility: Num;
  max_drawdown: Num;
  total_return: Num;
}

export interface AssetInfo {
  name: string;
  kind: AssetKind;
  currency: string | null;
  /** e.g. ["Stocks", "AI Supply Chain", "Energy"] */
  categories: string[];
  /** "Theme / Segment", e.g. "AI Supply Chain / Power" */
  segments: string[];
  /** market-cap rank, crypto only */
  rank: number | null;
}

export interface MarketRow extends SummaryStats, AssetInfo {
  market_id: string;
  modelled: boolean;
  last_close: number;
  change_1d: Num;
  spark: number[];
}

export interface PriceRow {
  date: string;
  open: Num;
  high: Num;
  low: Num;
  close: number;
  volume: Num;
  return_1d: Num;
  cumulative_return: Num;
  drawdown: Num;
  rolling_vol_30d: Num;
}

export interface Prices extends AssetInfo {
  market_id: string;
  available_range: [string, string];
  sources: string[];
  summary: SummaryStats;
  rows: PriceRow[];
}

export interface Correlation {
  ids: string[];
  matrix: Num[][];
}

export interface Company {
  company_id: string;
  company_name: string;
  ticker: string | null;
  is_public: boolean;
  exchange: string | null;
  country: string | null;
  region: string | null;
  industry: string | null;
  active_from: string | null;
  active_to: string | null;
  currency: string | null;
  themes: string[];
  segments: string[];
  ingested: boolean;
}

export interface ThemeMember {
  entity_id: string;
  theme: string;
  segment: string;
  subsegment: string | null;
  role_notes: string | null;
  name: string;
  ticker: string | null;
  country: string | null;
  region: string | null;
  kind: "stock" | "etf" | "private";
  ingested: boolean;
}

export interface Companies {
  companies: Company[];
  themes: string[];
  /** segments per theme, upstream to downstream */
  segments: Record<string, string[]>;
  regions: string[];
  theme_members: ThemeMember[];
}

export interface SeriesPoint {
  date: string;
  value: number;
}

export interface IndexSummary {
  annualized_volatility: Num;
  cumulative_return: Num;
  max_drawdown: Num;
  sharpe_ratio: Num;
  beta?: Record<string, Num>;
}

export interface Indices {
  index_members: Record<string, string[]>;
  missing_members?: Record<string, string[]> | string[];
  indices: Record<string, IndexSummary>;
  cumulative_return: Record<string, SeriesPoint[]>;
  rolling_corr_vs_spx: Record<string, SeriesPoint[]>;
}

export interface EventRow {
  event_id: string;
  event_date: string;
  event_type: string;
  organisation: string | null;
  primary_market_id: string | null;
  title: string;
  description: string;
  /** curated catalogue, or detected automatically from news headlines */
  source: "curated" | "news";
  n_articles?: number | null;
}

export interface EventOutcome {
  event_id: string;
  market_id: string | null;
  event_date: string;
  title: string;
  status: string;
  t0_raw_return?: Num;
  t0_abnormal_return?: Num;
  cumulative_abnormal_return_full_window?: Num;
}

export interface Events {
  events: EventRow[];
  benchmark: string | null;
  window: number | null;
  outcomes: EventOutcome[];
  abnormal_returns: Record<string, { day: number; value: number }[]>;
  caar: { day: number; AAR: Num; CAAR: Num; n_events: number }[];
}

export interface CoveragePeriod {
  days: number;
  covered: number;
  pct: Num;
}

export interface Coverage {
  by_market: Record<string, Record<"train" | "validation" | "test", CoveragePeriod>>;
  totals: Record<"train" | "validation" | "test", CoveragePeriod>;
  training_gate?: { threshold: number; value: number; met: boolean };
}

export interface SentimentSummary {
  models: string[];
  model: string | null;
  labels: string[];
  n_scored?: number;
  distribution: { label: string; count: number }[];
  by_entity: { matched_company_id: string; mean_sentiment: Num; n_articles: number; std_sentiment: Num }[];
  daily: {
    date: string;
    mean_sentiment: Num;
    sentiment_volatility: Num;
    news_volume: number;
    positive_ratio: Num;
    negative_ratio: Num;
  }[];
  coverage: Coverage | null;
}

export interface NewsItem {
  news_id: string;
  timestamp: string;
  title: string;
  source: string;
  source_id: string | null;
  url: string | null;
  entity: string | null;
  asset_type: string | null;
  matched_company_id: string | null;
  matched_asset_id: string | null;
  sentiment_score: Num;
  sentiment_label: string | null;
}

export interface NewsPage {
  total: number;
  page: number;
  page_size: number;
  model?: string | null;
  items: NewsItem[];
  facets: { sources?: string[]; entities?: string[]; labels?: string[] };
}

export interface Metrics {
  n?: number;
  positive_rate?: Num;
  accuracy?: Num;
  precision?: Num;
  recall?: Num;
  specificity?: Num;
  f1?: Num;
  balanced_accuracy?: Num;
  roc_auc?: Num;
  pr_auc?: Num;
  brier_score?: Num;
  suspiciously_high_auc?: boolean;
  confusion_matrix?: { tn: number; fp: number; fn: number; tp: number };
}

export interface ModelEntry {
  validation_metrics: Metrics;
  train_metrics?: Metrics;
  train_time_seconds?: number;
  inference_time_seconds?: number;
  train_val_pr_auc_gap?: Num;
}

export interface ModelReport {
  horizon: number;
  n_train: number;
  n_validation: number;
  train_positive_rate: Num;
  val_positive_rate: Num;
  models: Record<string, ModelEntry>;
  leaderboard_criteria: string[];
  leaderboard: string[];
  any_suspiciously_high_auc: boolean;
}

/** Validation labels and per-model probabilities, for curves and threshold-dependent confusion matrices. */
export interface ValidationPredictions {
  horizon: number;
  n_validation: number;
  base_rate: Num;
  y_true: number[];
  models: Record<string, Num[]>;
  /** baselines' predictions are fixed, not thresholded */
  baselines: Record<string, { tn: number; fp: number; fn: number; tp: number }>;
}

export interface FeatureValue {
  feature: string;
  importance?: Num;
  mean_abs_shap?: Num;
  importance_mean?: Num;
  importance_std?: Num;
}

export interface Explainability {
  horizon: number;
  models: string[];
  importance: Record<string, FeatureValue[]>;
  shap: Record<string, FeatureValue[]>;
  permutation: Record<string, FeatureValue[]>;
  agreement: { feature: string; n_models_in_top_n: number; models: string[] }[];
}

export interface Predictions {
  horizon: number;
  target: string;
  validation_positive_rate: Num;
  leaderboard: string[];
  assets: { market_id: string; as_of: string; close: number }[];
  models: Record<string, { validation_pr_auc: Num; validation_roc_auc: Num; probabilities: Record<string, number> }>;
}

export interface JobSpec {
  name: string;
  label: string;
  description: string;
}

export interface Job {
  id: string;
  name: string;
  status: "running" | "succeeded" | "failed";
  returncode: number | null;
  started_at: string;
  finished_at: string | null;
  command: string;
  log_tail?: string;
}

export interface JobList {
  available: JobSpec[];
  running: string | null;
  history: Job[];
}
