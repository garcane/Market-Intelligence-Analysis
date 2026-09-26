import { useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";
import { CheckCircle2, Loader2, Play, XCircle } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { useJob, useJobs, useMeta, useRunJob } from "../api/client";
import type { Job } from "../api/types";
import { Badge, Button, Card, EmptyState, ErrorState, PageHeader, Skeleton } from "../components/ui";
import { relativeTime, shortDate } from "../lib/format";

// Recommended order after new data arrives.
const ORDER = ["ingest", "news_backfill", "sentiment", "features", "target", "split", "train", "explain", "indices", "event_study"];

function StatusBadge({ status }: { status: Job["status"] }) {
  if (status === "running") return <Badge tone="blue"><Loader2 className="size-3 animate-spin" aria-hidden />running</Badge>;
  if (status === "succeeded") return <Badge tone="gain"><CheckCircle2 className="size-3" aria-hidden />succeeded</Badge>;
  return <Badge tone="loss"><XCircle className="size-3" aria-hidden />failed</Badge>;
}

function duration(job: Job): string {
  const end = job.finished_at ? Date.parse(job.finished_at) : Date.now();
  const s = Math.max(0, Math.round((end - Date.parse(job.started_at)) / 1000));
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${s % 60}s`;
}

export default function Pipeline() {
  const meta = useMeta();
  const enabled = Boolean(meta.data?.pipeline_enabled);
  const jobs = useJobs(enabled);
  const run = useRunJob();
  const queryClient = useQueryClient();
  const [activeId, setActiveId] = useState<string | null>(null);
  const [maxRequests, setMaxRequests] = useState("100");
  const job = useJob(activeId ?? jobs.data?.running ?? null);
  const logRef = useRef<HTMLPreElement>(null);
  const lastStatus = useRef<string | undefined>(undefined);

  // When a job finishes, every cached dataset may be stale.
  useEffect(() => {
    const status = job.data?.status;
    if (lastStatus.current === "running" && status && status !== "running") {
      queryClient.invalidateQueries();
    }
    lastStatus.current = status;
  }, [job.data?.status, queryClient]);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
  }, [job.data?.log_tail]);

  if (meta.data && !enabled) {
    return (
      <>
        <PageHeader title="Pipeline" />
        <EmptyState title="Pipeline runs are disabled">
          This is a read-only deployment. Pipeline runs are only available when the app runs locally.
        </EmptyState>
      </>
    );
  }

  const running = Boolean(jobs.data?.running);
  const available = [...(jobs.data?.available ?? [])].sort((a, b) => ORDER.indexOf(a.name) - ORDER.indexOf(b.name));

  const start = (name: string) => {
    const cap = name === "news_backfill" ? Number(maxRequests) || undefined : undefined;
    run.mutate({ name, maxRequests: cap }, { onSuccess: (j) => setActiveId(j.id) });
  };

  return (
    <>
      <PageHeader
        title="Pipeline"
        description="Re-run pipeline stages on this machine. One job runs at a time; pages refresh when it finishes. Only visible when the app runs locally."
      />

      {run.error && <div className="mb-6"><ErrorState error={run.error} /></div>}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-5">
        <Card title="Stages" subtitle="In the order they depend on each other" className="xl:col-span-2" bodyClassName="p-3">
          {jobs.isLoading ? <Skeleton className="h-96" /> : jobs.error ? <ErrorState error={jobs.error} /> : (
            <ol className="flex flex-col gap-1">
              {available.map((spec, i) => (
                <li key={spec.name} className="flex items-start gap-3 rounded-xl p-3 hover:bg-surface">
                  <span className="tabular grid size-6 shrink-0 place-items-center rounded-full bg-surface text-[12px] font-semibold text-steel">{i + 1}</span>
                  <div className="min-w-0 flex-1">
                    <div className="text-[14px] font-medium">{spec.label}</div>
                    <div className="text-[13px] text-steel">{spec.description}</div>
                    {spec.name === "news_backfill" && (
                      <label className="mt-2 flex items-center gap-2 text-[12px] text-steel">
                        Max requests
                        <input type="number" min={1} max={5000} value={maxRequests} onChange={(e) => setMaxRequests(e.target.value)}
                          className="tabular h-8 w-24 rounded-full border border-hairline-strong px-3 text-[13px] text-ink" />
                      </label>
                    )}
                  </div>
                  <Button variant="secondary" className="min-h-9 px-3" disabled={running || run.isPending}
                    onClick={() => start(spec.name)} aria-label={`Run ${spec.label}`}>
                    <Play className="size-3.5" aria-hidden /> Run
                  </Button>
                </li>
              ))}
            </ol>
          )}
        </Card>

        <div className="flex min-w-0 flex-col gap-6 xl:col-span-3">
          <Card
            title={job.data ? available.find((a) => a.name === job.data!.name)?.label ?? job.data.name : "Job output"}
            subtitle={job.data ? <code className="text-[12px]">{job.data.command}</code> : "Start a stage to see its output here"}
            action={job.data && (
              <div className="flex items-center gap-2 text-[13px] text-steel">
                <StatusBadge status={job.data.status} />{duration(job.data)}
              </div>
            )}
          >
            <pre ref={logRef} aria-live="polite"
              className="h-80 overflow-auto rounded-xl bg-ink p-4 font-mono text-[12px] leading-relaxed whitespace-pre-wrap text-[#e7e8ee]">
              {job.data?.log_tail || (job.data ? "Waiting for output…" : "No job selected.")}
            </pre>
          </Card>

          <Card title="Recent runs" subtitle="This server session only">
            {jobs.data?.history.length ? (
              <ul className="flex flex-col">
                {jobs.data.history.map((h) => (
                  <li key={h.id}>
                    <button onClick={() => setActiveId(h.id)}
                      className={clsx("flex w-full items-center gap-3 border-b border-hairline-soft py-2.5 text-left text-[14px] last:border-0 hover:bg-surface-soft",
                        h.id === (activeId ?? jobs.data?.running) && "font-medium")}>
                      <span className="min-w-0 flex-1 truncate">{available.find((a) => a.name === h.name)?.label ?? h.name}</span>
                      <StatusBadge status={h.status} />
                      <span className="tabular w-16 text-right text-[12px] text-steel">{duration(h)}</span>
                      <span className="w-20 text-right text-[12px] text-steel" title={shortDate(h.started_at)}>{relativeTime(h.started_at)}</span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : <p className="text-[14px] text-steel">No runs yet.</p>}
          </Card>
        </div>
      </div>
    </>
  );
}
