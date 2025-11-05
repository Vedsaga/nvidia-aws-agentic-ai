"use client";
import React from "react";
import { cn } from "@/lib/utils";

interface AppLayoutProps {
  documentList: React.ReactNode;
  mainPanel: React.ReactNode;
  referencePanel?: React.ReactNode;
  hasReferencePanel?: boolean;
}

export default function AppLayout({
  documentList,
  mainPanel,
  referencePanel,
  hasReferencePanel = false,
}: AppLayoutProps) {
  return (
    <div className="flex min-h-screen w-full bg-zinc-50 dark:bg-black">
      <div className="flex h-screen w-full bg-white shadow-sm">
        <aside className="w-80 shrink-0 border-r border-zinc-200 bg-zinc-50/40">
          {documentList}
        </aside>
        <main
          className={cn(
            "flex-1 overflow-hidden transition-[width] duration-300 ease-in-out",
            hasReferencePanel ? "w-[50%]" : "w-full",
          )}
        >
          {mainPanel}
        </main>
        <aside
          className={cn(
            "shrink-0 border-l border-zinc-200 bg-white transition-all duration-300 ease-in-out",
            hasReferencePanel ? "w-[35%] translate-x-0 opacity-100" : "w-0 -translate-x-4 opacity-0 pointer-events-none",
          )}
        >
          <div className="h-full overflow-hidden">{hasReferencePanel ? referencePanel : null}</div>
        </aside>
      </div>
    </div>
  );
}
