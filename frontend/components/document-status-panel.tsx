"use client";
import React from "react";
import { useStatus } from "@/hooks/useStatus";

export default function DocumentStatusPanel({ jobId }: { jobId?: string }) {
  const { data, isLoading } = useStatus(jobId ?? undefined);

  const status = (data as any)?.status ?? (data as any)?.Status ?? "-";
  const progress = (data as any)?.progress_percentage ?? (data as any)?.progress_percentage ?? 0;

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
