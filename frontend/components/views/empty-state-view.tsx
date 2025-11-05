"use client";
import React from "react";
import { FilePlus2 } from "lucide-react";

export default function EmptyStateView() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 bg-white px-10 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 text-primary">
        <FilePlus2 className="h-8 w-8" />
      </div>
      <div className="space-y-2">
        <h2 className="text-xl font-semibold text-foreground">Upload your first document</h2>
        <p className="max-w-md text-sm text-muted-foreground">
          Bring your .txt files into KārakaKG to generate a knowledge graph. Once uploaded, we will process the
          document and unlock the chat assistant for querying.
        </p>
      </div>
    </div>
  );
}
