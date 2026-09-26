import { createColumnHelper } from "@tanstack/react-table";
import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import { useExplainability } from "../api/client";
import type { Explainability as Data, FeatureValue } from "../api/types";
import { Chart } from "../components/Chart";
import { DataTable } from "../components/DataTable";
import { Badge, Card, EmptyState, PageHeader, PillTabs, QueryState } from "../components/ui";
import { horizontalBars, numFmt } from "../lib/charts";
import { humanize } from "../lib/format";

const TOP_N = 15;
type Agreement = Data["agreement"][number];
const col = createColumnHelper<Agreement>();
const agreementColumns = [
  col.accessor("feature", { header: "Feature", cell: (c) => <code className="text-[13px]">{c.getValue()}</code> }),
  col.accessor("n_models_in_top_n", {
    header: "Models agreeing",
    meta: { align: "right" },
    cell: (c) => <Badge tone={c.getValue() >= 3 ? "gain" : c.getValue() === 2 ? "teal" : "neutral"}>{c.getValue()}</Badge>,
  }),
  col.accessor("models", {
    header: "Which models",
    enableSorting: false,
    cell: (c) => <span className="text-[13px] text-slate">{c.getValue().map(humanize).join(", ")}</span>,
  }),
];

function bars(rows: FeatureValue[] | undefined, key: Exclude<keyof FeatureValue, "feature">, signed = false) {
  if (!rows?.length) return null;
  const top = [...rows]
    .sort((a, b) => Math.abs(b[key] ?? 0) - Math.abs(a[key] ?? 0))
    .slice(0, TOP_N)
    .map((r) => ({ label: r.feature, value: r[key] ?? null }));
  return horizontalBars(top, { format: numFmt(3), signed, color: "#8b5cf6" });
}

export default function Explainability() {
  const explain = useExplainability(5);
  const [params, setParams] = useSearchParams();
  const model = params.get("model") ?? explain.data?.models[0] ?? "";

  const charts = useMemo(() => {
    const d = explain.data;
    if (!d || !model) return null;
    return {
      importance: bars(d.importance[model], "importance", model === "logistic_regression"),
      shap: bars(d.shap[model], "mean_abs_shap"),
      permutation: bars(d.permutation[model], "importance_mean", true),
    };
  }, [explain.data, model]);

  const panels = [
    { key: "permutation", title: "Permutation importance", subtitle: "Drop in validation PR-AUC when the feature is shuffled; model-agnostic" },
    { key: "shap", title: "Mean |SHAP|", subtitle: "Average contribution to each prediction" },
    { key: "importance", title: model === "logistic_regression" ? "Coefficients" : "Built-in importance",
      subtitle: model === "logistic_regression" ? "Standardised features, so sizes are comparable" : "Impurity- or gain-based, from the fitted model" },
  ] as const;

  return (
    <>
      <PageHeader
        title="Explainability"
        description="Which features drive each model's predictions, and where different models agree. Agreement across methods is stronger evidence than any single ranking."
        actions={explain.data && (
          <PillTabs label="Model" value={model} onChange={(m) => setParams({ model: m }, { replace: true })}
            options={explain.data.models.map((m) => ({ value: m, label: humanize(m) }))} />
        )}
      />
      <QueryState query={explain} skeleton="h-[600px]">
        {(d) => (
          <>
            <div className="mb-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
              {panels.map((p) => {
                const option = charts?.[p.key];
                return (
                  <Card key={p.key} title={p.title} subtitle={p.subtitle}>
                    {option
                      ? <Chart option={option} height={440} ariaLabel={`${p.title} for ${humanize(model)}`} />
                      : <EmptyState title="Not computed">{humanize(model)} has no {p.title.toLowerCase()} output.</EmptyState>}
                  </Card>
                );
              })}
            </div>
            <Card title="Cross-model agreement" subtitle={`Features in the top ranks of several models (horizon ${d.horizon} days)`}>
              <DataTable data={d.agreement} columns={agreementColumns} dense initialSort={[{ id: "n_models_in_top_n", desc: true }]} caption="Feature agreement across models" />
            </Card>
          </>
        )}
      </QueryState>
    </>
  );
}
