"use client";
import React, { useMemo, useState } from "react";
import { Loader2, RefreshCw, Activity, Network } from "lucide-react";
import { useProcessingChain } from "@/hooks/useProcessingChain";
import { triggerProcessing, isApiError } from "@/lib/api";
import type { JobStatus } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast-provider";
import { formatStatusLabel } from "@/lib/status";
import type { UseQueryResult } from "@tanstack/react-query";

interface ProcessingViewProps {
  jobId: string;
  documentName?: string;
  statusQuery: UseQueryResult<JobStatus | null>;
}

export default function ProcessingView({ jobId, documentName, statusQuery }: ProcessingViewProps) {
  const { notify } = useToast();
  const [isRetrying, setIsRetrying] = useState(false);
  const processingChainQuery = useProcessingChain(jobId, true);

  const statusData = statusQuery.data ?? null;
  const progress = Math.min(Math.max(statusData?.progress_percentage ?? 0, 0), 100);
  const totalSentences = statusData?.total_sentences ?? 0;
  const completedSentences = statusData?.completed_sentences ?? 0;
  const llmCalls = statusData?.llm_calls_made ?? 0;
  const statusLabel = formatStatusLabel(statusData?.status ?? "Processing");

  const hasConnectionIssue = statusQuery.failureCount >= 3;
  const processingChainEntries = processingChainQuery.data?.entries ?? [];
  const chainLoadFailed = isApiError(processingChainQuery.error) && processingChainQuery.error.status === 502;

  const formattedChain = useMemo(() => {
    return processingChainEntries.map((entry, index) => ({
      id: `${entry.stage}-${entry.timestamp}-${index}`,
      stage: formatStatusLabel(entry.stage),
      timestamp: entry.timestamp ? new Date(entry.timestamp).toLocaleTimeString() : "--",
      status: formatStatusLabel(entry.status ?? "running"),
      duration: entry.duration_ms ? `${entry.duration_ms}ms` : undefined,
      sentenceNumber: entry.sentence_number,
      message: entry.message,
    }));
  }, [processingChainEntries]);

  const handleRetryTrigger = async () => {
    setIsRetrying(true);
    try {
      await triggerProcessing(jobId);
      notify({
        title: "Processing restarted",
        description: `${documentName ?? "Document"} is queued for processing again.`,
      });
    } catch (error) {
      const message = isApiError(error)
        ? error.message
        : "Could not restart processing. Please try again.";
      notify({
        title: "Retry failed",
        description: message,
        variant: "destructive",
      });
    } finally {
      setIsRetrying(false);
    }
  };

  return (
    <div className="flex h-full flex-col overflow-hidden bg-white">
      <div className="border-b border-zinc-200 px-6 py-4">
        <div className="flex flex-col gap-1">
          <h2 className="text-lg font-semibold text-foreground">Processing document</h2>
          <p className="text-sm text-muted-foreground">{documentName ?? "Preparing document"}</p>
        </div>
      </div>

      {hasConnectionIssue ? (
        <div className="flex items-center gap-2 bg-amber-100 px-6 py-3 text-sm text-amber-900">
          <Network className="h-4 w-4" />
          Connection issue: Retrying status…
        </div>
      ) : null}

      <div className="flex flex-1 flex-col gap-6 overflow-y-auto px-6 py-6">
        <section className="grid gap-4 md:grid-cols-3">
          <div className="rounded-lg border border-zinc-200 p-4">
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span>Status</span>
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
            </div>
            <p className="mt-2 text-lg font-semibold text-foreground">{statusLabel}</p>
          </div>
          <div className="rounded-lg border border-zinc-200 p-4">
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span>Sentences processed</span>
              <Activity className="h-4 w-4 text-primary" />
            </div>
            <p className="mt-2 text-lg font-semibold text-foreground">
              {completedSentences}/{totalSentences || "?"}
            </p>
            <p className="text-xs text-muted-foreground">LLM calls: {llmCalls}</p>
          </div>
          <div className="rounded-lg border border-zinc-200 p-4">
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span>Actions</span>
            </div>
            <Button
              variant="secondary"
              size="sm"
              className="mt-3 inline-flex items-center gap-2"
              onClick={handleRetryTrigger}
              disabled={isRetrying}
            >
              <RefreshCw className={isRetrying ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
              {isRetrying ? "Retrying…" : "Retry processing"}
            </Button>
          </div>
        </section>

        <section>
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-foreground">Progress</h3>
            <span className="text-xs text-muted-foreground">{progress}%</span>
          </div>
          <div className="h-3 w-full overflow-hidden rounded-full bg-zinc-100">
            <div
              className="h-full rounded-full bg-primary transition-[width] duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
        </section>

        <section>
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-foreground">Processing chain</h3>
            {processingChainQuery.isFetching ? (
              <span className="flex items-center gap-2 text-xs text-muted-foreground">
                <Loader2 className="h-3 w-3 animate-spin" /> Updating…
              </span>
            ) : null}
          </div>

          {chainLoadFailed ? (
            <div className="rounded-md border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
              Could not load processing log
            </div>
          ) : null}

          {!chainLoadFailed && formattedChain.length === 0 ? (
            <div className="rounded-md border border-dashed border-zinc-200 p-6 text-center text-sm text-muted-foreground">
              Awaiting processing updates…
            </div>
          ) : null}

          <ol className="space-y-3">
            {formattedChain.map((entry) => (
              <li key={entry.id} className="rounded-lg border border-zinc-200 bg-zinc-50/60 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-foreground">{entry.stage}</p>
                  <span className="text-xs text-muted-foreground">{entry.timestamp}</span>
                </div>
                <div className="mt-1 text-xs text-muted-foreground">
                  Status: {entry.status}
                  {entry.duration ? ` · Duration ${entry.duration}` : ""}
                  {entry.sentenceNumber != null ? ` · Sentence ${entry.sentenceNumber}` : ""}
                </div>
                {entry.message ? (
                  <p className="mt-2 text-xs text-muted-foreground">{entry.message}</p>
                ) : null}
              </li>
            ))}
          </ol>
        </section>
      </div>
    </div>
  );
}
