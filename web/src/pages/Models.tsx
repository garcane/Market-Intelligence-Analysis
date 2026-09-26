import { createColumnHelper } from "@tanstack/react-table";
import { AlertTriangle, ShieldCheck } from "lucide-react";
import { useMemo, useState } from "react";

import { figureUrl, useModelReport } from "../api/client";
import type { Metrics, ModelReport } from "../api/types";
import { Chart } from "../components/Chart";
import { DataTable } from "../components/DataTable";
import { Badge, Card, PageHeader, PillTabs, QueryState, StatCard } from "../components/ui";
import { horizontalBars, numFmt } from "../lib/charts";
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

function ConfusionMatrix({ name, m }: { name: string; m: Metrics }) {
  const cm = m.confusion_matrix;
  if (!cm) return null;
  const total = cm.tn + cm.fp + cm.fn + cm.tp || 1;
  const cells: [string, number, boolean][] = [
    ["True neg", cm.tn, true], ["False pos", cm.fp, false], ["False neg", cm.fn, false], ["True pos", cm.tp, true],
  ];
  return (
    <div className="rounded-card border border-hairline-soft p-4">
      <div className="mb-3 text-[14px] font-medium">{humanize(name)}</div>
      <div className="grid grid-cols-2 gap-1.5" role="table" aria-label={`Confusion matrix for ${humanize(name)}`}>
        {cells.map(([label, v, correct]) => (
          <div key={label} role="cell" className="rounded-lg p-2.5"
            style={{ background: correct ? `rgba(0,180,115,${0.08 + (v / total) * 0.6})` : `rgba(229,72,77,${0.06 + (v / total) * 0.6})` }}>
            <div className="text-[11px] text-charcoal/70">{label}</div>
            <div className="tabular text-[18px] font-medium">{v}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

const FIGURES = { roc: "13_roc_curves.png", pr: "13_pr_curves.png", confusion: "13_confusion_matrices.png" } as const;

export default function Models() {
  const report = useModelReport(5);
  const [figure, setFigure] = useState<keyof typeof FIGURES>("pr");

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

            <Card title="Confusion matrices" subtitle="Validation split, threshold 0.5" className="mb-6">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {view!.rows.map((row) => <ConfusionMatrix key={row.name} name={row.name} m={row} />)}
              </div>
            </Card>

            <Card
              title="Curves"
              subtitle="Rendered by the training pipeline"
              action={
                <PillTabs label="Figure" value={figure} onChange={setFigure}
                  options={[{ value: "pr", label: "Precision–recall" }, { value: "roc", label: "ROC" }, { value: "confusion", label: "Confusion" }]} />
              }
            >
              <img src={figureUrl(FIGURES[figure])} alt={`${figure.toUpperCase()} curves for each model on the validation split`}
                loading="lazy" className="mx-auto w-full max-w-4xl rounded-xl" />
            </Card>
          </>
        )}
      </QueryState>
    </>
  );
}
