"use client";
import React, { useMemo } from "react";
import { Loader2, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import EmptyStateView from "@/components/views/empty-state-view";
import ProcessingView from "@/components/views/processing-view";
import ChatView from "@/components/views/chat-view";
import ErrorView from "@/components/views/error-view";
import type { ChatMessage, DocumentRecord, ReferenceData } from "@/lib/types";
import { deriveDocumentStatus } from "@/lib/status";
import { useStatus } from "@/hooks/useStatus";
import { useToast } from "@/components/ui/toast-provider";
import { triggerProcessing, isApiError } from "@/lib/api";

interface MainPanelProps {
  activeDocument?: DocumentRecord | null;
  chatHistory: ChatMessage[];
  onChatHistoryChange: (messages: ChatMessage[]) => void;
  onReferenceClick: (reference: ReferenceData) => void;
}

function UploadingView({ filename }: { filename?: string }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 bg-white px-10 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 text-primary">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
      <div className="space-y-2">
        <h2 className="text-xl font-semibold text-foreground">Uploading document…</h2>
        <p className="max-w-md text-sm text-muted-foreground">
          {filename ? `${filename} is being uploaded.` : "We are preparing your document for processing."} This may take a few moments.
        </p>
      </div>
    </div>
  );
}

function PendingTriggerView({ filename, onRetry }: { filename?: string; onRetry: () => void }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 bg-white px-10 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-amber-100 text-amber-600">
        <FileText className="h-8 w-8" />
      </div>
      <div className="space-y-2">
        <h2 className="text-xl font-semibold text-foreground">Processing not started</h2>
        <p className="max-w-md text-sm text-muted-foreground">
          {filename ? `${filename}` : "This document"} is uploaded but processing has not started yet. Retry to trigger the pipeline.
        </p>
        <Button variant="secondary" onClick={onRetry} className="inline-flex items-center gap-2">
          Retry processing
        </Button>
      </div>
    </div>
  );
}

export default function MainPanel({ activeDocument, chatHistory, onChatHistoryChange, onReferenceClick }: MainPanelProps) {
  const { notify } = useToast();
  const jobId = activeDocument?.job_id;
  const derivedStatus = deriveDocumentStatus(activeDocument?.status);
  const shouldFetchStatus = Boolean(jobId) && derivedStatus !== "uploading";

  const statusQuery = useStatus(jobId, shouldFetchStatus);
  const liveStatusString = statusQuery.data?.status ?? activeDocument?.status;
  const liveStatus = deriveDocumentStatus(liveStatusString);

  const failureMessage =
    statusQuery.data?.failure_reason ??
    statusQuery.data?.error_message ??
    activeDocument?.failure_reason ??
    activeDocument?.error_message;

  const handleRetry = async () => {
    if (!jobId) return;
    try {
      await triggerProcessing(jobId);
      notify({
        title: "Processing triggered",
        description: `${activeDocument?.filename ?? "Document"} has been queued for processing.`,
      });
    } catch (error) {
      const message = isApiError(error) ? error.message : "Could not trigger processing. Please try again.";
      notify({
        title: "Trigger failed",
        description: message,
        variant: "destructive",
      });
    }
  };

  const chatDisabledReason = useMemo(() => {
    if (liveStatus !== "completed") {
      return "Chat will be enabled once processing is complete.";
    }
    return undefined;
  }, [liveStatus]);

  if (!activeDocument || !jobId) {
    return <EmptyStateView />;
  }

  if (derivedStatus === "uploading") {
    return <UploadingView filename={activeDocument.filename} />;
  }

  if (derivedStatus === "pending" && liveStatus !== "processing" && liveStatus !== "completed") {
    return <PendingTriggerView filename={activeDocument.filename} onRetry={handleRetry} />;
  }

  if (liveStatus === "processing" || liveStatus === "queued" || liveStatus === "pending") {
    return <ProcessingView jobId={jobId} documentName={activeDocument.filename} statusQuery={statusQuery} />;
  }

  if (liveStatus === "failed") {
    return (
      <ErrorView
        title="Processing failed"
  message={failureMessage ?? "The document could not be processed."}
        onRetry={handleRetry}
        retryLabel="Retry processing"
      />
    );
  }

  return (
    <ChatView
      jobId={jobId}
      documentName={activeDocument.filename}
      history={chatHistory}
      onHistoryChange={onChatHistoryChange}
      onReferenceClick={onReferenceClick}
      disabledReason={chatDisabledReason}
    />
  );
}
