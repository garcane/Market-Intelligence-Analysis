import clsx from "clsx";
import { AlertTriangle, Inbox, RefreshCw } from "lucide-react";
import type { ButtonHTMLAttributes, ReactNode } from "react";

import { ApiError } from "../api/client";

export function Card({ title, subtitle, action, children, className, bodyClassName }: {
  title?: ReactNode;
  subtitle?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <section className={clsx("min-w-0 rounded-card border border-hairline-soft bg-canvas", className)}>
      {(title || action) && (
        <header className="flex flex-wrap items-start justify-between gap-3 px-5 pt-5">
          <div className="min-w-0">
            {title && <h2 className="text-[17px] leading-snug">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-[13px] text-steel">{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      <div className={clsx("p-5", bodyClassName)}>{children}</div>
    </section>
  );
}

const TONES = {
  white: "bg-canvas border border-hairline-soft",
  yellow: "bg-brand-yellow",
  teal: "bg-teal-light",
  coral: "bg-coral-light",
  rose: "bg-rose-light",
  orange: "bg-orange-light",
  lavender: "bg-lavender",
} as const;

export type Tone = keyof typeof TONES;

export function StatCard({ label, value, hint, tone = "white", valueClassName }: {
  label: ReactNode;
  value: ReactNode;
  hint?: ReactNode;
  tone?: Tone;
  valueClassName?: string;
}) {
  return (
    <div className={clsx("min-w-0 rounded-[20px] p-4 sm:p-5", TONES[tone])}>
      <div className="text-[13px] font-medium text-charcoal/80">{label}</div>
      <div className={clsx("tabular mt-2 truncate text-[22px] leading-tight font-medium tracking-tight sm:text-[28px]", valueClassName)}>
        {value}
      </div>
      {hint && <div className="mt-1 text-[13px] text-charcoal/70">{hint}</div>}
    </div>
  );
}

export function PageHeader({ title, description, actions }: {
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="max-w-3xl min-w-0">
        <h1 className="text-[28px] leading-tight tracking-[-0.5px] sm:text-[36px]">{title}</h1>
        {description && <p className="mt-2 text-[15px] text-slate">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

const BADGE = {
  neutral: "bg-surface text-slate",
  yellow: "bg-surface-yellow text-yellow-dark",
  blue: "bg-lavender text-brand-blue",
  coral: "bg-coral-light text-coral-dark",
  teal: "bg-teal-light text-moss",
  gain: "bg-gain-soft text-gain",
  loss: "bg-loss-soft text-loss",
  dark: "bg-ink text-canvas",
} as const;

export type BadgeTone = keyof typeof BADGE;

export function Badge({ tone = "neutral", children, className }: {
  tone?: BadgeTone;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span className={clsx("inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[12px] font-semibold whitespace-nowrap",
      BADGE[tone], className)}>
      {children}
    </span>
  );
}

export function Button({ variant = "primary", className, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost";
}) {
  return (
    <button
      {...props}
      className={clsx(
        "inline-flex min-h-10 items-center justify-center gap-2 rounded-full px-5 text-[14px] font-medium transition-colors disabled:cursor-not-allowed",
        variant === "primary" && "bg-ink text-canvas hover:bg-charcoal disabled:bg-hairline disabled:text-muted",
        variant === "secondary" && "border border-hairline-strong bg-canvas text-ink hover:bg-surface disabled:text-muted",
        variant === "ghost" && "text-ink hover:bg-surface",
        className,
      )}
    />
  );
}

/** Single-select pill tabs. `value` is the selected option's value. */
export function PillTabs<T extends string>({ options, value, onChange, label }: {
  options: { value: T; label: ReactNode }[];
  value: T;
  onChange: (value: T) => void;
  label: string;
}) {
  return (
    <div role="tablist" aria-label={label} className="flex flex-wrap gap-2">
      {options.map((o) => (
        <button
          key={o.value}
          role="tab"
          aria-selected={o.value === value}
          onClick={() => onChange(o.value)}
          className={clsx(
            "min-h-9 rounded-full border px-4 text-[14px] font-medium transition-colors",
            o.value === value ? "border-ink bg-ink text-canvas" : "border-hairline bg-canvas text-steel hover:text-ink",
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

/** Multi-select filter pills; an empty selection means "all". */
export function FilterPills({ options, selected, onChange, label }: {
  options: string[];
  selected: string[];
  onChange: (selected: string[]) => void;
  label: string;
}) {
  const toggle = (o: string) =>
    onChange(selected.includes(o) ? selected.filter((s) => s !== o) : [...selected, o]);
  return (
    <div role="group" aria-label={label} className="flex flex-wrap gap-2">
      {options.map((o) => {
        const on = selected.includes(o);
        return (
          <button
            key={o}
            aria-pressed={on}
            onClick={() => toggle(o)}
            className={clsx(
              "min-h-8 rounded-full border px-3 text-[13px] font-medium transition-colors",
              on ? "border-ink bg-ink text-canvas" : "border-hairline-strong bg-canvas text-charcoal hover:bg-surface",
            )}
          >
            {o}
          </button>
        );
      })}
      {selected.length > 0 && (
        <button onClick={() => onChange([])} className="min-h-8 px-2 text-[13px] font-medium text-brand-blue">
          Clear
        </button>
      )}
    </div>
  );
}

export function Select({ label, value, onChange, options, className }: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  className?: string;
}) {
  return (
    <label className={clsx("flex flex-col gap-1 text-[13px] font-medium text-steel", className)}>
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-10 rounded-full border border-hairline-strong bg-canvas px-4 text-[14px] text-ink"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </label>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={clsx("animate-pulse rounded-card bg-hairline-soft", className)} />;
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-card border border-dashed border-hairline-strong px-6 py-10 text-center">
      <Inbox className="size-6 text-stone" aria-hidden />
      <div className="font-medium">{title}</div>
      {children && <div className="max-w-md text-[14px] text-steel">{children}</div>}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const missing = error instanceof ApiError && error.status === 404;
  const message = error instanceof Error ? error.message : String(error);
  return (
    <div role="alert" className="flex flex-col items-center gap-3 rounded-card border border-coral-light bg-loss-soft/60 px-6 py-8 text-center">
      <AlertTriangle className="size-6 text-loss" aria-hidden />
      <div className="font-medium">{missing ? "Data not available yet" : "Couldn't load this data"}</div>
      <div className="max-w-lg text-[14px] text-slate">{message}</div>
      {onRetry && !missing && (
        <Button variant="secondary" onClick={onRetry}>
          <RefreshCw className="size-4" aria-hidden /> Try again
        </Button>
      )}
    </div>
  );
}

/** Renders loading / error / content for a TanStack query. */
export function QueryState<T>({ query, children, skeleton = "h-64" }: {
  query: { data: T | undefined; isLoading: boolean; error: unknown; refetch: () => unknown };
  children: (data: T) => ReactNode;
  skeleton?: string;
}) {
  if (query.isLoading) return <Skeleton className={skeleton} />;
  if (query.error) return <ErrorState error={query.error} onRetry={() => query.refetch()} />;
  if (query.data === undefined) return null;
  return <>{children(query.data)}</>;
}

export function Delta({ value, digits = 1 }: { value: number | null | undefined; digits?: number }) {
  if (value === null || value === undefined) return <span className="text-stone">—</span>;
  return (
    <span className={clsx("tabular font-medium", value > 0 ? "text-gain" : value < 0 ? "text-loss" : "text-slate")}>
      {value > 0 ? "+" : ""}
      {(value * 100).toFixed(digits)}%
    </span>
  );
}
