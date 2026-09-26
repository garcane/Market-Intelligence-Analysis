import { createColumnHelper } from "@tanstack/react-table";
import { Search } from "lucide-react";
import { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { useCompanies } from "../api/client";
import type { Company } from "../api/types";
import { DataTable } from "../components/DataTable";
import { Badge, Card, FilterPills, PageHeader, QueryState } from "../components/ui";

const col = createColumnHelper<Company>();

const columns = [
  col.accessor("company_name", { header: "Company", cell: (c) => <span className="font-medium">{c.getValue()}</span> }),
  col.accessor("ticker", {
    header: "Ticker",
    cell: (c) => {
      const t = c.getValue();
      if (!t) return <span className="text-stone">private</span>;
      return c.row.original.ingested
        ? <Link to={`/stocks/${t}`} className="font-semibold text-brand-blue hover:underline" onClick={(e) => e.stopPropagation()}>{t}</Link>
        : <span className="font-semibold">{t}</span>;
    },
  }),
  col.accessor("region", { header: "Region" }),
  col.accessor("country", { header: "Country" }),
  col.accessor("ai_categories", {
    header: "AI categories",
    enableSorting: false,
    cell: (c) => (
      <div className="flex flex-wrap gap-1">
        {c.getValue().map((cat) => <Badge key={cat} tone="blue">{cat}</Badge>)}
      </div>
    ),
  }),
  col.accessor("ingested", {
    header: "Price data",
    cell: (c) => (c.getValue() ? <Badge tone="gain">ingested</Badge> : <Badge>—</Badge>),
  }),
];

const splitParam = (v: string | null) => (v ? v.split("|").filter(Boolean) : []);

export default function Companies() {
  const companies = useCompanies();
  const [params, setParams] = useSearchParams();
  const categories = splitParam(params.get("category"));
  const regions = splitParam(params.get("region"));
  const q = params.get("q") ?? "";

  const update = (key: string, value: string) =>
    setParams((p) => { if (value) p.set(key, value); else p.delete(key); return p; }, { replace: true });

  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return (companies.data?.companies ?? []).filter((c) =>
      (!categories.length || c.ai_categories.some((cat) => categories.includes(cat))) &&
      (!regions.length || (c.region !== null && regions.includes(c.region))) &&
      (!needle || c.company_name.toLowerCase().includes(needle) || (c.ticker ?? "").toLowerCase().includes(needle)));
  }, [companies.data, categories, regions, q]);

  return (
    <>
      <PageHeader
        title="Company explorer"
        description="Every company in the AI universe, public or private, with its role in the AI value chain and whether its prices are ingested."
      />
      <QueryState query={companies} skeleton="h-[600px]">
        {(d) => (
          <Card
            title={`${rows.length} of ${d.companies.length} companies`}
            action={
              <label className="relative block w-full sm:w-64">
                <span className="sr-only">Search companies</span>
                <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-stone" aria-hidden />
                <input
                  value={q}
                  onChange={(e) => update("q", e.target.value)}
                  placeholder="Search name or ticker"
                  className="h-10 w-full rounded-lg border border-hairline bg-surface pr-3 pl-9 text-[14px] placeholder:text-muted"
                />
              </label>
            }
          >
            <div className="mb-5 flex flex-col gap-3">
              <div>
                <div className="mb-2 text-[12px] font-semibold tracking-[0.5px] text-stone uppercase">AI category</div>
                <FilterPills label="AI category" options={d.categories} selected={categories} onChange={(s) => update("category", s.join("|"))} />
              </div>
              <div>
                <div className="mb-2 text-[12px] font-semibold tracking-[0.5px] text-stone uppercase">Region</div>
                <FilterPills label="Region" options={d.regions} selected={regions} onChange={(s) => update("region", s.join("|"))} />
              </div>
            </div>
            <DataTable data={rows} columns={columns} initialSort={[{ id: "company_name", desc: false }]} caption="Companies" />
          </Card>
        )}
      </QueryState>
    </>
  );
}
