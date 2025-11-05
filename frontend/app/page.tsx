"use client";
import React, { useMemo, useState } from "react";
import DocumentList from "@/components/document-list";
import AppLayout from "@/components/layout/app-layout";
import MainPanel from "@/components/main-panel";
import KnowledgeReferencePanel from "@/components/reference-panel";
import type { ChatMessage, DocumentRecord, ReferenceData } from "@/lib/types";

export default function HomePage() {
  const [activeDocument, setActiveDocument] = useState<DocumentRecord | null>(null);
  const [activeReference, setActiveReference] = useState<ReferenceData | null>(null);
  const [chatHistoryByJob, setChatHistoryByJob] = useState<Record<string, ChatMessage[]>>({});

  const activeJobId = activeDocument?.job_id;
  const activeHistory = useMemo<ChatMessage[]>(() => {
    if (!activeJobId) return [];
    return chatHistoryByJob[activeJobId] ?? [];
  }, [activeJobId, chatHistoryByJob]);

  const handleDocumentSelect = (document: DocumentRecord) => {
    setActiveDocument(document);
    setActiveReference(null);
  };

  const handleHistoryChange = (messages: ChatMessage[]) => {
    if (!activeJobId) return;
    setChatHistoryByJob((prev) => {
      if (prev[activeJobId] === messages) {
        return prev;
      }
      return {
        ...prev,
        [activeJobId]: messages,
      };
    });
  };

  const handleReferenceClick = (reference: ReferenceData) => {
    setActiveReference(reference);
  };

  return (
    <AppLayout
      documentList={<DocumentList activeDocument={activeDocument} onSelect={handleDocumentSelect} />}
      mainPanel={
        <MainPanel
          activeDocument={activeDocument}
          chatHistory={activeHistory}
          onChatHistoryChange={handleHistoryChange}
          onReferenceClick={handleReferenceClick}
        />
      }
      hasReferencePanel={Boolean(activeReference)}
      referencePanel={
        activeReference ? <KnowledgeReferencePanel reference={activeReference} onClose={() => setActiveReference(null)} /> : undefined
      }
    />
  );
}
