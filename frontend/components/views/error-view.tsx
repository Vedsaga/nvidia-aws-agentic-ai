"use client";
import React from "react";
import { AlertOctagon, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ErrorViewProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  retryLabel?: string;
}

export default function ErrorView({ title = "Processing failed", message, onRetry, retryLabel = "Retry" }: ErrorViewProps) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 bg-white px-10 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-destructive/10 text-destructive">
        <AlertOctagon className="h-8 w-8" />
      </div>
      <div className="space-y-2">
        <h2 className="text-xl font-semibold text-foreground">{title}</h2>
        <p className="max-w-md text-sm text-muted-foreground">
          {message ?? "The document encountered an error during processing. Review the details and retry when ready."}
        </p>
      </div>
      {onRetry ? (
        <Button variant="secondary" onClick={onRetry} className="inline-flex items-center gap-2">
          <RotateCcw className="h-4 w-4" />
          {retryLabel}
        </Button>
      ) : null}
    </div>
  );
}
