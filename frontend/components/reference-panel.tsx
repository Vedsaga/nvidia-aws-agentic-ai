"use client";
import React from "react";
import { X, GitBranch, ListTree } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ReferenceData } from "@/lib/types";
import { useSentenceChain } from "@/hooks/useSentenceChain";
import { formatStatusLabel } from "@/lib/status";

interface KnowledgeReferencePanelProps {
  reference?: ReferenceData | null;
  onClose: () => void;
}

export default function KnowledgeReferencePanel({ reference, onClose }: KnowledgeReferencePanelProps) {
  const sentenceHash = reference?.sentence_hash;
  const sentenceChainQuery = useSentenceChain(sentenceHash);
  const sentenceChain = sentenceChainQuery.data?.processing_stages ?? [];
  const sentenceChainFailed = sentenceChainQuery.isError;

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <header className="flex items-start justify-between border-b border-zinc-200 px-6 py-4">
        <div>
          <h2 className="text-lg font-semibold text-foreground">Reference details</h2>
          {reference?.sentence_text ? (
            <p className="mt-2 text-sm text-muted-foreground">“{reference.sentence_text}”</p>
          ) : (
            <p className="text-sm text-muted-foreground">Select a reference to view knowledge graph details.</p>
          )}
        </div>
        <Button variant="ghost" size="sm" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </header>

      {!reference ? (
        <div className="flex flex-1 items-center justify-center px-10 text-center text-sm text-muted-foreground">
          Choose a reference from the chat to inspect its knowledge graph context.
        </div>
      ) : (
        <div className="flex-1 space-y-6 overflow-y-auto px-6 py-6">
          <section className="rounded-lg border border-zinc-200 bg-white p-4">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <GitBranch className="h-4 w-4" /> Knowledge graph snippet
            </h3>
            <pre className="mt-3 max-h-60 overflow-auto rounded bg-zinc-950/90 p-4 text-xs text-white">
              {JSON.stringify(reference.kg_snippet, null, 2)}
            </pre>
            <div className="mt-3 grid gap-3 text-xs text-muted-foreground">
              <div>
                <strong className="font-medium text-foreground">Nodes:</strong>
                {reference.kg_snippet?.nodes?.length ? (
                  <ul className="ml-4 list-disc">
                    {reference.kg_snippet.nodes.map((node) => (
                      <li key={node.id}>
                        {node.label} ({node.node_type ?? "entity"})
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="ml-4">No nodes available.</p>
                )}
              </div>
              <div>
                <strong className="font-medium text-foreground">Edges:</strong>
                {reference.kg_snippet?.edges?.length ? (
                  <ul className="ml-4 list-disc">
                    {reference.kg_snippet.edges.map((edge, index) => (
                      <li key={`${edge.source}-${edge.target}-${index}`}>
                        {edge.source} → {edge.target} ({edge.label})
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="ml-4">No edges available.</p>
                )}
              </div>
            </div>
          </section>

          <section className="rounded-lg border border-zinc-200 bg-white p-4">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <ListTree className="h-4 w-4" /> Sentence processing chain
            </h3>
            {sentenceChainFailed ? (
              <div className="mt-3 rounded border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
                Could not load sentence processing details
              </div>
            ) : null}

            {!sentenceChainFailed && sentenceChain.length === 0 ? (
              <p className="mt-3 text-sm text-muted-foreground">Awaiting sentence-level processing details…</p>
            ) : null}

            <ol className="mt-4 space-y-3">
              {sentenceChain.map((stage, index) => (
                <li key={`${stage.stage}-${index}`} className="rounded-md border border-zinc-200 bg-zinc-50/80 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-semibold text-foreground">{formatStatusLabel(stage.stage)}</p>
                    <span className="text-xs text-muted-foreground">
                      {stage.timestamp ? new Date(stage.timestamp).toLocaleTimeString() : "--"}
                    </span>
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    Status: {formatStatusLabel(stage.status ?? "completed")}
                    {stage.duration_ms ? ` · Duration ${stage.duration_ms}ms` : ""}
                  </div>
                </li>
              ))}
            </ol>
          </section>
        </div>
      )}
    </div>
  );
}
