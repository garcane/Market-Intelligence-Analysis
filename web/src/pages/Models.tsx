import { createColumnHelper } from "@tanstack/react-table";
import { AlertTriangle, ShieldCheck } from "lucide-react";
import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import { useModelReport, useValidationPredictions } from "../api/client";
import type { Metrics, ModelReport, ValidationPredictions } from "../api/types";
import { Chart } from "../components/Chart";
import { DataTable } from "../components/DataTable";
import { Badge, Card, PageHeader, PillTabs, QueryState, StatCard } from "../components/ui";
import { type Confusion, confusionAt, pointAt, prCurve, rates, rocCurve } from "../lib/classification";
import { horizontalBars, numFmt, xyCurves } from "../lib/charts";
import { compact, humanize, num, pct } from "../lib/format";

type Row = Metrics & { name: string; rank: number | null; baseline: boolean; gap: number | null | undefined };
const col = createColumnHelper<Row>();
const metric = (key: keyof Metrics, header: string, format: (v: number | null) => string = (v) => num(v, 3)) =>
  col.accessor((r) => (r[key] as number | null | undefined) ?? null, { id: key, header, cell: (c) => format(c.getValue()), meta: { align: "right" } });

const columns = [
  col.accessor("name", {
    header: "Model",
    cell: (c) => (
      <span className="flex items-center gap-2 font-medium">
        {c.row.original.rank === 1 && <Badge tone="yellow">#1</Badge>}
        {humanize(c.getValue())}
        {c.row.original.baseline && <Badge>baseline</Badge>}
      </span>
    ),
  }),
  metric("pr_auc", "PR-AUC"),
  metric("roc_auc", "ROC-AUC"),
  metric("balanced_accuracy", "Bal. acc"),
  metric("f1", "F1"),
  metric("precision", "Precision"),
  metric("recall", "Recall"),
  metric("brier_score", "Brier"),
  col.accessor("gap", {
    header: "Train−val PR gap",
    meta: { align: "right" },
    cell: (c) => {
      const v = c.getValue();
      return v === null || v === undefined ? "—" : <span className={v > 0.15 ? "font-semibold text-loss" : ""}>{num(v, 3)}</span>;
    },
  }),
];

function ConfusionMatrix({ name, cm, fixed }: { name: string; cm: Confusion; fixed?: boolean }) {
  const total = cm.tn + cm.fp + cm.fn + cm.tp || 1;
  const r = rates(cm);
  const cells: [string, number, boolean][] = [
    ["True neg", cm.tn, true], ["False pos", cm.fp, false], ["False neg", cm.fn, false], ["True pos", cm.tp, true],
  ];
  return (
    <div className="rounded-card border border-hairline-soft p-4">
      <div className="mb-3 flex items-center justify-between gap-2">
        <span className="text-[14px] font-medium">{humanize(name)}</span>
        {fixed && <Badge>fixed</Badge>}
      </div>
      <div className="grid grid-cols-2 gap-1.5" role="table" aria-label={`Confusion matrix for ${humanize(name)}`}>
        {cells.map(([label, v, correct]) => (
          <div key={label} role="cell" title={`${label}: ${v} of ${total} rows (${pct(v / total, 1)})`}
            className="rounded-lg p-2.5 transition-colors"
            style={{ background: correct ? `rgba(0,180,115,${0.08 + (v / total) * 0.6})` : `rgba(229,72,77,${0.06 + (v / total) * 0.6})` }}>
            <div className="text-[11px] text-charcoal/70">{label}</div>
            <div className="tabular text-[18px] font-medium">{v}</div>
          </div>
        ))}
      </div>
      <div className="tabular mt-3 flex justify-between text-[12px] text-steel">
        <span>Precision {pct(r.precision, 1)}</span>
        <span>Recall {pct(r.recall, 1)}</span>
      </div>
    </div>
  );
}

type Figure = "pr" | "roc" | "confusion";
const FIGURES: Figure[] = ["pr", "roc", "confusion"];
const DEFAULT_THRESHOLD = 0.5;

/** PR / ROC curves and threshold-driven confusion matrices, all from per-row validation predictions. */
function Curves({ preds, report }: { preds: ValidationPredictions; report: ModelReport }) {
  // tab and threshold live in the URL (?curve=roc&t=0.4) so a view can be shared
  const [params, setParams] = useSearchParams();
  const figure = FIGURES.find((f) => f === params.get("curve")) ?? "pr";
  const parsed = Number(params.get("t"));
  const threshold = Number.isFinite(parsed) && parsed >= 0.05 && parsed <= 0.95 && params.has("t") ? parsed : DEFAULT_THRESHOLD;
  const setParam = (key: string, value: string | null) =>
    setParams((p) => { if (value === null) p.delete(key); else p.set(key, value); return p; }, { replace: true });
  const setFigure = (f: Figure) => setParam("curve", f === "pr" ? null : f);
  const setThreshold = (t: number) => setParam("t", t === DEFAULT_THRESHOLD ? null : t.toFixed(2));

  // leaderboard order, then any other exported model
  const names = useMemo(
    () => [...report.leaderboard.filter((n) => n in preds.models), ...Object.keys(preds.models).filter((n) => !report.leaderboard.includes(n))],
    [preds, report],
  );
  const curves = useMemo(() => Object.fromEntries(names.map((n) => [n, {
    roc: rocCurve(preds.y_true, preds.models[n]),
    pr: prCurve(preds.y_true, preds.models[n]),
  }])), [names, preds]);

  const option = useMemo(() => {
    const metric = (n: string, key: "pr_auc" | "roc_auc") => num(report.models[n]?.validation_metrics[key] ?? null, 3);
    if (figure === "roc") {
      return xyCurves(names.map((n) => ({ name: `${humanize(n)} · AUC ${metric(n, "roc_auc")}`, points: curves[n].roc, marker: pointAt(curves[n].roc, threshold) })),
        { xName: "False positive rate", yName: "True positive rate", reference: { label: "Chance", points: [[0, 0], [1, 1]] } });
    }
    const base = preds.base_rate ?? 0;
    return xyCurves(names.map((n) => ({ name: `${humanize(n)} · AP ${metric(n, "pr_auc")}`, points: curves[n].pr, marker: pointAt(curves[n].pr, threshold) })),
      { xName: "Recall", yName: "Precision", reference: { label: `Base rate ${pct(base, 0)}`, points: [[0, base], [1, base]] } });
  }, [figure, names, curves, threshold, report, preds.base_rate]);

  return (
    <Card
      title="Curves"
      subtitle={`Validation split, ${preds.n_validation.toLocaleString()} rows · hover for values, scroll to zoom, click the legend to hide a model`}
      action={
        <PillTabs<Figure> label="Figure" value={figure} onChange={setFigure}
          options={[{ value: "pr", label: "Precision–recall" }, { value: "roc", label: "ROC" }, { value: "confusion", label: "Confusion" }]} />
      }
    >
      <div className="mb-4 flex flex-wrap items-center gap-3 rounded-2xl bg-surface px-4 py-3">
        <label htmlFor="threshold" className="text-[13px] font-medium text-slate">
          Decision threshold <span className="tabular ml-1 text-ink">{threshold.toFixed(2)}</span>
        </label>
        <input id="threshold" type="range" min={0.05} max={0.95} step={0.01} value={threshold}
          onChange={(e) => setThreshold(Number(e.target.value))} className="min-w-40 flex-1 accent-brand-blue" />
        <button onClick={() => setThreshold(DEFAULT_THRESHOLD)} disabled={threshold === DEFAULT_THRESHOLD}
          className="rounded-full px-3 py-1 text-[13px] font-medium text-brand-blue disabled:text-muted">
          Reset to 0.5
        </button>
        <span className="w-full text-[12px] text-steel">
          A row is predicted positive when its probability is at or above the threshold. Dots on the curves mark each model at this threshold.
        </span>
      </div>

      {figure === "confusion" ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {names.map((n) => <ConfusionMatrix key={n} name={n} cm={confusionAt(preds.y_true, preds.models[n], threshold)} />)}
          {Object.entries(preds.baselines).map(([n, cm]) => <ConfusionMatrix key={n} name={n} cm={cm} fixed />)}
        </div>
      ) : (
        <Chart option={option} height={460}
          ariaLabel={figure === "pr" ? "Precision-recall curves for each model on the validation split" : "ROC curves for each model on the validation split"} />
      )}
    </Card>
  );
}

export default function Models() {
  const report = useModelReport(5);
  const preds = useValidationPredictions(5);

  const view = useMemo(() => {
    const r: ModelReport | undefined = report.data;
    if (!r) return null;
    const rows: Row[] = Object.entries(r.models).map(([name, entry]) => ({
      ...entry.validation_metrics,
      name,
      rank: r.leaderboard.includes(name) ? r.leaderboard.indexOf(name) + 1 : null,
      baseline: name.startsWith("baseline"),
      gap: entry.train_val_pr_auc_gap,
    }));
    const bars = horizontalBars(
      [...rows].sort((a, b) => (b.pr_auc ?? 0) - (a.pr_auc ?? 0)).map((row) => ({ label: humanize(row.name), value: row.pr_auc ?? null })),
      { format: numFmt(3), reference: r.val_positive_rate !== null ? { value: r.val_positive_rate, label: "base rate" } : undefined },
    );
    return { rows, bars, best: r.leaderboard[0] };
  }, [report.data]);

  const r = report.data;

  return (
    <>
      <PageHeader
        title="Model performance"
        description={`Classifiers predicting whether an asset's ${r?.horizon ?? 5}-day forward return beats the threshold. All scores are on the validation split; the test split stays untouched.`}
      />
      <QueryState query={report} skeleton="h-[600px]">
        {(data) => (
          <>
            <div className={`mb-6 flex items-start gap-3 rounded-2xl p-4 text-[14px] ${data.any_suspiciously_high_auc ? "bg-loss-soft text-loss" : "bg-gain-soft text-gain"}`}>
              {data.any_suspiciously_high_auc ? <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden /> : <ShieldCheck className="mt-0.5 size-4 shrink-0" aria-hidden />}
              <p>
                {data.any_suspiciously_high_auc
                  ? "At least one model has a suspiciously high ROC-AUC. Check for target leakage before trusting these results."
                  : "No model shows a suspiciously high ROC-AUC, a basic check against target leakage."}
              </p>
            </div>

            <div className="mb-6 grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
              <StatCard tone="yellow" label="Best model" value={humanize(view!.best ?? "—")}
                hint={`PR-AUC ${num(data.models[view!.best]?.validation_metrics.pr_auc, 3)}`} />
              <StatCard tone="teal" label="Training rows" value={compact(data.n_train)} hint={`${pct(data.train_positive_rate, 0)} positive`} />
              <StatCard tone="lavender" label="Validation rows" value={compact(data.n_validation)} hint={`${pct(data.val_positive_rate, 0)} positive`} />
              <StatCard tone="rose" label="Ranked by" value={humanize(data.leaderboard_criteria[0] ?? "—")}
                hint={data.leaderboard_criteria.slice(1).map(humanize).join(", ")} />
            </div>

            <div className="mb-6 grid grid-cols-1 gap-6">
              <Card title="PR-AUC by model" subtitle="Dashed line: the positive rate, which a random classifier scores">
                <Chart option={view!.bars} height={280} ariaLabel="Validation PR-AUC for each model against the base rate" />
              </Card>
              <Card title="Validation metrics" subtitle="Threshold 0.5 for the classification metrics">
                <DataTable data={view!.rows} columns={columns} dense initialSort={[{ id: "pr_auc", desc: true }]} caption="Validation metrics by model" />
              </Card>
            </div>

            <QueryState query={preds} skeleton="h-[560px]">
              {(p) => <Curves preds={p} report={data} />}
            </QueryState>
          </>
        )}
      </QueryState>
    </>
  );
}
