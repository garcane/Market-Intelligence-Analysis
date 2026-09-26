import clsx from "clsx";
import { Info } from "lucide-react";
import { Link } from "react-router-dom";

import { usePredictions } from "../api/client";
import type { Predictions as Data } from "../api/types";
import { Badge, Card, PageHeader, QueryState } from "../components/ui";
import { humanize, num, pct, price, shortDate } from "../lib/format";

function ProbabilityBar({ value, baseRate }: { value: number; baseRate: number | null }) {
  const above = baseRate !== null && value > baseRate;
  return (
    <div className="relative h-2.5 w-full rounded-full bg-hairline-soft" aria-hidden>
      <div className={clsx("h-full rounded-full", above ? "bg-gain-fill" : "bg-stone")} style={{ width: `${value * 100}%` }} />
      {baseRate !== null && <div className="absolute -top-1 h-4.5 w-0.5 rounded bg-ink" style={{ left: `${baseRate * 100}%` }} />}
    </div>
  );
}

function AssetCard({ asset, data }: { asset: Data["assets"][number]; data: Data }) {
  const models = data.leaderboard.filter((m) => data.models[m]);
  const probs = models.map((m) => data.models[m].probabilities[asset.market_id]).filter((p) => p !== undefined);
  const mean = probs.length ? probs.reduce((a, b) => a + b, 0) / probs.length : null;
  const base = data.validation_positive_rate;
  const signal = mean === null || base === null ? null : mean - base;

  return (
    <div className="flex flex-col gap-4 rounded-card border border-hairline-soft bg-canvas p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <Link to={`/stocks/${asset.market_id}`} className="text-[20px] font-semibold hover:text-brand-blue">{asset.market_id}</Link>
          <div className="text-[13px] text-steel">close {price(asset.close)} · as of {shortDate(asset.as_of)}</div>
        </div>
        {signal !== null && (
          <Badge tone={signal > 0.05 ? "gain" : signal < -0.05 ? "coral" : "neutral"}>
            {signal > 0.05 ? "above base rate" : signal < -0.05 ? "below base rate" : "near base rate"}
          </Badge>
        )}
      </div>
      <div>
        <div className="text-[12px] text-steel">Average probability across models</div>
        <div className="tabular text-[32px] leading-tight font-medium tracking-tight">{pct(mean, 0)}</div>
      </div>
      <ul className="flex flex-col gap-2.5">
        {models.map((m) => {
          const p = data.models[m].probabilities[asset.market_id];
          if (p === undefined) return null;
          return (
            <li key={m}>
              <div className="mb-1 flex justify-between text-[13px]">
                <span className="text-charcoal">{humanize(m)}</span>
                <span className="tabular font-medium">{pct(p, 0)}</span>
              </div>
              <ProbabilityBar value={p} baseRate={base} />
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export default function Predictions() {
  const predictions = usePredictions(5);
  const d = predictions.data;

  return (
    <>
      <PageHeader
        title="Predictions"
        description={d ? `Each model's probability of a ${d.target}, scored on the latest data available.` : "Latest model probabilities per asset."}
      />
      <div className="mb-6 flex items-start gap-3 rounded-2xl bg-surface-yellow p-4 text-[14px] text-yellow-dark">
        <Info className="mt-0.5 size-4 shrink-0" aria-hidden />
        <p>
          <b>Research output, not investment advice.</b> These models score only modestly above chance on validation data
          (PR-AUC around {d ? num(Math.max(...Object.values(d.models).map((m) => m.validation_pr_auc ?? 0)), 2) : "0.4"} against a
          base rate of {pct(d?.validation_positive_rate ?? null, 0)}). The black tick on each bar marks that base rate: the share of
          validation days on which the event actually happened.
        </p>
      </div>
      <QueryState query={predictions} skeleton="h-[500px]">
        {(data) => (
          <>
            <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              {data.assets.map((a) => <AssetCard key={a.market_id} asset={a} data={data} />)}
            </div>
            <Card title="Models" subtitle="Ordered by the validation leaderboard">
              <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
                {data.leaderboard.filter((m) => data.models[m]).map((m, i) => (
                  <li key={m} className="rounded-2xl bg-surface p-4">
                    <div className="flex items-center gap-2 text-[14px] font-medium">
                      <Badge tone={i === 0 ? "yellow" : "neutral"}>#{i + 1}</Badge>{humanize(m)}
                    </div>
                    <div className="tabular mt-2 text-[13px] text-steel">
                      PR-AUC {num(data.models[m].validation_pr_auc, 3)} · ROC-AUC {num(data.models[m].validation_roc_auc, 3)}
                    </div>
                  </li>
                ))}
              </ul>
            </Card>
          </>
        )}
      </QueryState>
    </>
  );
}
