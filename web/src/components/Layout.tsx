import clsx from "clsx";
import {
  Activity,
  BarChart3,
  Brain,
  Building2,
  CalendarClock,
  CandlestickChart,
  Gauge,
  LayoutDashboard,
  Lightbulb,
  Menu,
  Moon,
  Network,
  Zap,
  Newspaper,
  PlayCircle,
  ShieldAlert,
  Smile,
  Sun,
  X,
  type LucideIcon,
} from "lucide-react";
import { Suspense, useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

import { useMeta } from "../api/client";
import { shortDate } from "../lib/format";
import { useTheme } from "../lib/theme";
import { Skeleton } from "./ui";

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  localOnly?: boolean;
}

const NAV: { group: string; items: NavItem[] }[] = [
  {
    group: "Markets",
    items: [
      { to: "/", label: "Overview", icon: LayoutDashboard },
      { to: "/ai-market", label: "AI market", icon: BarChart3 },
      { to: "/stocks", label: "Stocks", icon: CandlestickChart },
      { to: "/risk", label: "Risk analytics", icon: ShieldAlert },
    ],
  },
  {
    group: "Research",
    items: [
      { to: "/companies", label: "Company explorer", icon: Building2 },
      { to: "/supply-chain", label: "AI supply chain", icon: Network },
      { to: "/energy", label: "Energy", icon: Zap },
      { to: "/events", label: "AI events", icon: CalendarClock },
    ],
  },
  {
    group: "Sentiment",
    items: [
      { to: "/sentiment", label: "Sentiment", icon: Smile },
      { to: "/news", label: "News feed", icon: Newspaper },
    ],
  },
  {
    group: "Models",
    items: [
      { to: "/models", label: "Model performance", icon: Gauge },
      { to: "/explainability", label: "Explainability", icon: Lightbulb },
      { to: "/predictions", label: "Predictions", icon: Brain },
    ],
  },
  {
    group: "Operations",
    items: [{ to: "/pipeline", label: "Pipeline", icon: PlayCircle, localOnly: true }],
  },
];

function Wordmark() {
  return (
    <div className="flex items-center gap-2.5">
      <span className="grid size-8 place-items-center rounded-lg bg-[#ffd02f]" aria-hidden>
        <Activity className="size-4.5 text-[#1c1c1e]" strokeWidth={2.5} />
      </span>
      <span className="text-[15px] leading-tight font-semibold">
        AI Market
        <br />
        <span className="font-medium text-steel">Intelligence</span>
      </span>
    </div>
  );
}

function Nav({ pipelineEnabled, onNavigate }: { pipelineEnabled: boolean; onNavigate?: () => void }) {
  return (
    <nav aria-label="Main" className="flex flex-col gap-5">
      {NAV.map(({ group, items }) => {
        const visible = items.filter((i) => !i.localOnly || pipelineEnabled);
        if (!visible.length) return null;
        return (
          <div key={group}>
            <div className="mb-1.5 px-3 text-[11px] font-semibold tracking-[0.5px] text-stone uppercase">{group}</div>
            <ul className="flex flex-col gap-0.5">
              {visible.map(({ to, label, icon: Icon }) => (
                <li key={to}>
                  <NavLink
                    to={to}
                    end={to === "/"}
                    onClick={onNavigate}
                    className={({ isActive }) =>
                      clsx(
                        "flex min-h-10 items-center gap-3 rounded-full px-3 text-[14px] font-medium transition-colors",
                        isActive ? "bg-ink text-canvas" : "text-charcoal hover:bg-surface",
                      )
                    }
                  >
                    <Icon className="size-4 shrink-0" aria-hidden />
                    {label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        );
      })}
    </nav>
  );
}

function ThemeToggle({ withLabel = false }: { withLabel?: boolean }) {
  const { theme, toggle } = useTheme();
  const dark = theme === "dark";
  const Icon = dark ? Sun : Moon;
  return (
    <button
      onClick={toggle}
      aria-pressed={dark}
      aria-label="Dark theme"
      title={dark ? "Switch to light theme" : "Switch to dark theme"}
      className={clsx(
        "flex min-h-10 items-center gap-3 rounded-full border border-hairline text-[14px] font-medium text-charcoal transition-colors hover:bg-surface",
        withLabel ? "w-full px-3" : "size-10 justify-center",
      )}
    >
      <Icon className="size-4 shrink-0" aria-hidden />
      {withLabel && (dark ? "Light theme" : "Dark theme")}
    </button>
  );
}

function Freshness() {
  const meta = useMeta();
  if (!meta.data) return null;
  const m = meta.data;
  return (
    <div className="rounded-2xl bg-surface p-3 text-[12px] leading-relaxed text-steel">
      <div>
        Prices to <span className="font-medium text-ink">{shortDate(m.latest_price_date)}</span>
      </div>
      <div>
        <span className="font-medium text-ink">{m.news_count.toLocaleString()}</span> articles ·{" "}
        <span className="font-medium text-ink">{m.scored_articles.toLocaleString()}</span> scored
      </div>
      {m.mode === "public" && <div className="mt-1">Read-only demo</div>}
    </div>
  );
}

export function Layout() {
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const meta = useMeta();
  const pipelineEnabled = Boolean(meta.data?.pipeline_enabled);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <div className="min-h-dvh">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:rounded-full focus:bg-ink focus:px-4 focus:py-2 focus:text-canvas">
        Skip to content
      </a>

      {/* desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 hidden w-64 flex-col gap-6 overflow-y-auto border-r border-hairline-soft bg-canvas px-4 py-5 lg:flex">
        <Wordmark />
        <Nav pipelineEnabled={pipelineEnabled} />
        <div className="mt-auto flex flex-col gap-3">
          <ThemeToggle withLabel />
          <Freshness />
        </div>
      </aside>

      {/* mobile top bar + drawer */}
      <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-hairline-soft bg-canvas/95 px-4 backdrop-blur lg:hidden">
        <Wordmark />
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <button
            onClick={() => setOpen(true)}
            aria-label="Open navigation"
            aria-expanded={open}
            className="grid size-10 place-items-center rounded-full border border-hairline"
          >
            <Menu className="size-5" aria-hidden />
          </button>
        </div>
      </header>
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Navigation">
          <div className="absolute inset-0 bg-ink/30" onClick={() => setOpen(false)} />
          <div className="absolute inset-y-0 left-0 flex w-[min(20rem,85vw)] flex-col gap-6 overflow-y-auto bg-canvas px-4 py-4 shadow-float">
            <div className="flex items-center justify-between">
              <Wordmark />
              <button onClick={() => setOpen(false)} aria-label="Close navigation" className="grid size-10 place-items-center rounded-full border border-hairline">
                <X className="size-5" aria-hidden />
              </button>
            </div>
            <Nav pipelineEnabled={pipelineEnabled} onNavigate={() => setOpen(false)} />
            <Freshness />
          </div>
        </div>
      )}

      <main id="main" className="px-4 pt-6 pb-16 sm:px-6 lg:ml-64 lg:px-10 lg:pt-10">
        <div className="mx-auto max-w-[1280px]">
          <Suspense fallback={<Skeleton className="h-96" />}>
            <Outlet />
          </Suspense>
        </div>
      </main>
    </div>
  );
}
