"use client";
import React, { useMemo, useState, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Loader2, CheckCircle2, AlertTriangle, FileText, RefreshCcw } from "lucide-react";
import UploadButton from "./upload-button";
import { useDocuments } from "@/hooks/useDocuments";
import type { DocumentRecord } from "@/lib/types";
import { deriveDocumentStatus, formatStatusLabel } from "@/lib/status";
import { cn } from "@/lib/utils";

interface DocumentListProps {
  activeDocument?: DocumentRecord | null;
  onSelect: (document: DocumentRecord | null) => void;
}

interface PendingDocument extends DocumentRecord {
  isPending: true;
}

export default function DocumentList({ activeDocument, onSelect }: DocumentListProps) {
  const queryClient = useQueryClient();
  const documentsQuery = useDocuments();
  const [pendingDocs, setPendingDocs] = useState<PendingDocument[]>([]);
  const [tempToJobId, setTempToJobId] = useState<Record<string, string>>({});

  const resolveJobId = useCallback((tempId: string) => tempToJobId[tempId] ?? tempId, [tempToJobId]);

  const documents = useMemo<DocumentRecord[]>(() => {
    const fetched = documentsQuery.data ?? [];
    const sortedFetched = [...fetched].sort((a, b) => {
      const aTime = a.created_at ? new Date(a.created_at).getTime() : 0;
      const bTime = b.created_at ? new Date(b.created_at).getTime() : 0;
      return bTime - aTime;
    });
    const allDocs = [...pendingDocs, ...sortedFetched];
    const seen = new Set<string>();
    const unique: DocumentRecord[] = [];
    for (const doc of allDocs) {
      const jobId = doc.job_id;
      if (!jobId || seen.has(jobId)) continue;
      seen.add(jobId);
      unique.push(doc);
    }
    return unique;
  }, [pendingDocs, documentsQuery.data]);

  const activeJobId = activeDocument?.job_id;

  const handleUploadStart = (tempId: string, filename: string) => {
    const optimisticDoc: PendingDocument = {
      job_id: tempId,
      filename,
      status: "uploading",
      isPending: true,
    };
    setPendingDocs((prev) => [optimisticDoc, ...prev]);
    setTempToJobId((prev) => ({ ...prev, [tempId]: tempId }));
    onSelect(optimisticDoc);
  };

  const handleUploadReady = (tempId: string, payload: DocumentRecord) => {
    setPendingDocs((prev) =>
      prev.map((doc) =>
        doc.job_id === tempId
          ? {
              ...payload,
              isPending: true,
            }
          : doc,
      ),
    );
    setTempToJobId((prev) => ({ ...prev, [tempId]: payload.job_id }));
    onSelect({ ...payload, status: payload.status ?? "uploading" });
  };

  const handleUploadComplete = (tempId: string, payload: DocumentRecord) => {
    const resolvedJobId = resolveJobId(tempId);
    setPendingDocs((prev) => prev.filter((doc) => doc.job_id !== tempId && doc.job_id !== resolvedJobId));
    setTempToJobId((prev) => {
      const { [tempId]: _removed, ...rest } = prev;
      return rest;
    });
    queryClient.invalidateQueries({ queryKey: ["documents"] });
    onSelect(payload);
  };

  const handleUploadError = (tempId: string, _message: string) => {
    const resolvedJobId = resolveJobId(tempId);
    setPendingDocs((prev) => prev.filter((doc) => doc.job_id !== tempId && doc.job_id !== resolvedJobId));
    setTempToJobId((prev) => {
      const { [tempId]: _removed, ...rest } = prev;
      return rest;
    });
    if (activeDocument?.job_id === tempId || activeDocument?.job_id === resolvedJobId) {
      onSelect(null);
    }
  };

  const handleSelect = (doc: DocumentRecord) => {
    onSelect(doc);
  };

  const renderStatusIcon = (doc: DocumentRecord) => {
    const status = deriveDocumentStatus(doc.status);
    if ((doc as PendingDocument).isPending) {
      return <Loader2 className="h-4 w-4 animate-spin text-primary" />;
    }
    if (status === "processing" || status === "uploading" || status === "queued") {
      return <Loader2 className="h-4 w-4 animate-spin text-primary" />;
    }
    if (status === "completed") {
      return <CheckCircle2 className="h-4 w-4 text-green-500" />;
    }
    if (status === "failed") {
      return <AlertTriangle className="h-4 w-4 text-destructive" />;
    }
    return <FileText className="h-4 w-4 text-muted-foreground" />;
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-zinc-200 px-4 py-4">
        <div>
          <h2 className="text-lg font-semibold text-foreground">Documents</h2>
          <p className="text-xs text-muted-foreground">Upload documents to process into knowledge graphs.</p>
        </div>
        <button
          type="button"
          className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-zinc-200 bg-white text-muted-foreground shadow-sm transition hover:bg-zinc-50"
          onClick={() => documentsQuery.refetch()}
          disabled={documentsQuery.isFetching}
          aria-label="Refresh documents"
        >
          <RefreshCcw className={cn("h-4 w-4", documentsQuery.isFetching ? "animate-spin" : "")} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4">
        {documentsQuery.isLoading && !documents.length ? (
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground">Loading documents…</div>
        ) : null}

        {documentsQuery.isError ? (
          <div className="mb-4 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
            Could not load documents. Please try again.
          </div>
        ) : null}

        {!documentsQuery.isLoading && documents.length === 0 ? (
          <div className="mt-8 text-sm text-muted-foreground">
            No documents yet. Upload a .txt file to get started.
          </div>
        ) : null}

        <div className="space-y-2">
          {documents.map((doc) => {
            const statusLabel = formatStatusLabel(doc.status);
            const isActive = activeJobId === doc.job_id;
            const isPending = (doc as PendingDocument).isPending;
            return (
              <button
                key={doc.job_id}
                type="button"
                onClick={() => handleSelect(doc)}
                className={cn(
                  "w-full rounded-md border border-transparent bg-white p-3 text-left shadow-sm transition hover:border-primary/40 hover:bg-primary/5",
                  isActive ? "border-primary bg-primary/10" : "",
                  isPending ? "opacity-80" : "",
                )}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-medium text-foreground">{doc.filename || "(unnamed document)"}</div>
                    <div className="mt-1 text-xs text-muted-foreground">
                      {isPending ? "Uploading…" : statusLabel}
                    </div>
                  </div>
                  {renderStatusIcon(doc)}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      <div className="border-t border-zinc-200 px-4 py-4">
        <UploadButton
          onUploadStart={handleUploadStart}
          onUploadReady={handleUploadReady}
          onUploadComplete={handleUploadComplete}
          onUploadError={handleUploadError}
          buttonSize="lg"
          buttonClassName="w-full justify-center text-base h-12"
        />
      </div>
    </div>
  );
}
