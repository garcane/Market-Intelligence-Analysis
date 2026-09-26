import { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { useCompanies } from "../api/client";
import { Chart } from "../components/Chart";
import { Badge, Card, PageHeader, PillTabs, QueryState } from "../components/ui";
import { horizontalBars, numFmt } from "../lib/charts";

// The AI value chain, upstream to downstream.
const ORDER = [
  "Semiconductor Manufacturing", "Memory", "Compute", "Custom AI Silicon / Networking",
  "Cloud / AI Infrastructure", "AI Model Provider", "Consumer / Platform",
];

export default function SupplyChain() {
  const companies = useCompanies();
  const [params, setParams] = useSearchParams();

  const view = useMemo(() => {
    const d = companies.data;
    if (!d) return null;
    const categories = [...d.categories].sort((a, b) => {
      const ia = ORDER.indexOf(a), ib = ORDER.indexOf(b);
      return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
    });
    const counts = categories.map((c) => ({
      label: c,
      value: new Set(d.category_members.filter((m) => m.ai_category === c).map((m) => m.company_id)).size,
    }));
    return { categories, counts, ingested: new Set(d.companies.filter((c) => c.ingested).map((c) => c.company_id)) };
  }, [companies.data]);

  const selected = params.get("category") ?? view?.categories[0] ?? "";
  const members = (companies.data?.category_members ?? []).filter((m) => m.ai_category === selected);

  return (
    <>
      <PageHeader
        title="AI supply chain"
        description="Where each company sits in the AI value chain, from chip manufacturing to consumer platforms. A company can play several roles."
      />
      <QueryState query={companies} skeleton="h-[600px]">
        {() => (
          <>
            <Card title="Companies per stage" subtitle="Ordered upstream to downstream" className="mb-6">
              <Chart
                option={horizontalBars(view!.counts, { format: numFmt(0), color: "#0fbcb0" })}
                height={300}
                ariaLabel="Number of companies in each AI supply-chain category"
              />
            </Card>

            <div className="mb-4">
              <PillTabs
                label="Supply-chain stage"
                value={selected}
                onChange={(c) => setParams({ category: c }, { replace: true })}
                options={view!.categories.map((c) => ({ value: c, label: c }))}
              />
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              {members.map((m) => (
                <div key={`${m.company_id}-${m.ai_category}`} className="flex flex-col gap-2 rounded-card border border-hairline-soft bg-canvas p-5">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="text-[16px] font-medium">{m.company_name}</div>
                      <div className="text-[13px] text-steel">{[m.country, m.region].filter(Boolean).join(" · ")}</div>
                    </div>
                    {m.ticker ? (
                      view!.ingested.has(m.company_id)
                        ? <Link to={`/stocks/${m.ticker}`}><Badge tone="dark">{m.ticker}</Badge></Link>
                        : <Badge>{m.ticker}</Badge>
                    ) : <Badge>private</Badge>}
                  </div>
                  {m.subsector && <Badge tone="teal" className="self-start">{m.subsector}</Badge>}
                  {m.role_notes && <p className="text-[14px] leading-relaxed text-slate">{m.role_notes}</p>}
                </div>
              ))}
            </div>
          </>
        )}
      </QueryState>
    </>
  );
}
