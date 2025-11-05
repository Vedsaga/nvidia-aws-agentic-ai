"use client";
import React from "react";
import { useStatus } from "@/hooks/useStatus";
import type { JobStatus } from "@/lib/types";

export default function DocumentStatusPanel({ jobId }: { jobId?: string }) {
  const { data, isLoading } = useStatus(jobId ?? undefined);

  const status = (() => {
    const s = data?.status;
    if (typeof s === "string") return s;
    const alt = (data as JobStatus | null)?.["Status"];
    if (typeof alt === "string") return alt;
    return "-";
  })();

  const progress = (() => {
    const p = (data as JobStatus | null)?.progress_percentage;
    if (typeof p === "number") return p;
    const alt = (data as JobStatus | null)?.["progress_percentage"];
    if (typeof alt === "number") return alt;
    return 0;
  })();

  return (
    <div className="p-6">
      <h2 className="text-xl font-semibold mb-2">Document Status</h2>
      {!jobId && <div className="text-sm text-muted-foreground">Select a document to see details</div>}
      {jobId && (
        <div className="mt-4 space-y-4">
          <div className="flex items-center justify-between">
            <div className="text-sm text-zinc-600">Status</div>
            <div className="font-medium">{isLoading ? "Loading…" : status}</div>
          </div>

          <div>
            <div className="text-sm text-zinc-600 mb-1">Progress</div>
            <div className="w-full bg-slate-100 rounded h-3">
              <div className="bg-primary h-3 rounded" style={{ width: `${progress}%` }} />
            </div>
            <div className="text-xs text-zinc-500 mt-1">{progress}%</div>
          </div>

          <div>
            <h3 className="text-sm font-medium">Live Log (processing chain)</h3>
            <div className="mt-2 text-sm text-zinc-600">Logs and LLM call timeline will appear here (via /processing-chain).</div>
          </div>
        </div>
      )}
    </div>
  );
}
