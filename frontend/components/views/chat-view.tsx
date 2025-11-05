"use client";
import React, { useEffect, useMemo, useRef, useState } from "react";
import { SendHorizontal, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { postQuery, postQuerySubmit, getQueryStatus, isApiError } from "@/lib/api";
import type { ChatMessage, QueryResponse, ReferenceData } from "@/lib/types";
import { useToast } from "@/components/ui/toast-provider";

interface ChatViewProps {
  jobId: string;
  documentName?: string;
  history: ChatMessage[];
  onHistoryChange: (messages: ChatMessage[]) => void;
  onReferenceClick: (reference: ReferenceData) => void;
  disabledReason?: string;
}

interface PendingAsyncQuery {
  queryId: string;
  messageId: string;
}

export default function ChatView({
  jobId,
  documentName,
  history,
  onHistoryChange,
  onReferenceClick,
  disabledReason,
}: ChatViewProps) {
  const { notify } = useToast();
  const [messages, setMessages] = useState<ChatMessage[]>(history);
  const [inputValue, setInputValue] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [pendingAsync, setPendingAsync] = useState<PendingAsyncQuery | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setMessages(history);
  }, [history]);

  useEffect(() => {
    onHistoryChange(messages);
  }, [messages, onHistoryChange]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (!pendingAsync) return;
    const interval = setInterval(async () => {
      try {
        const status = await getQueryStatus(pendingAsync.queryId);
        if (status.status === "completed") {
          setMessages((prev) =>
            prev.map((message) =>
              message.id === pendingAsync.messageId
                ? {
                    ...message,
                    type: "assistant",
                    content: status.answer ?? "",
                    references: status.references ?? [],
                    timestamp: new Date(),
                  }
                : message,
            ),
          );
          setPendingAsync(null);
          setIsSending(false);
        } else if (status.status === "failed") {
          setMessages((prev) =>
            prev.map((message) =>
              message.id === pendingAsync.messageId
                ? {
                    ...message,
                    type: "error",
                    content: `Sorry, an error occurred: ${status.error ?? status.message ?? "Unknown error"}`,
                    references: [],
                    timestamp: new Date(),
                  }
                : message,
            ),
          );
          setPendingAsync(null);
          setIsSending(false);
        }
      } catch (error) {
        console.error("Failed to refresh async query status", error);
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [pendingAsync, notify]);

  const isInputDisabled = Boolean(disabledReason) || isSending || Boolean(pendingAsync);

  const appendMessage = (message: ChatMessage) => {
    setMessages((prev) => [...prev, message]);
  };

  const updateMessage = (messageId: string, updater: (message: ChatMessage) => ChatMessage) => {
    setMessages((prev) => prev.map((message) => (message.id === messageId ? updater(message) : message)));
  };

  const createMessage = (type: ChatMessage["type"], content: string, references?: ReferenceData[]): ChatMessage => ({
    id: crypto.randomUUID(),
    type,
    content,
    references,
    timestamp: new Date(),
  });

  const handleAsyncFallback = async (question: string, placeholderId: string) => {
    try {
      const response = await postQuerySubmit(question);
      setPendingAsync({ queryId: response.query_id, messageId: placeholderId });
    } catch (error) {
      const message = isApiError(error)
        ? error.message
        : "Async query submission failed. Please try again.";
      updateMessage(placeholderId, (existing) => ({
        ...existing,
        type: "error",
        content: `Sorry, an error occurred: ${message}`,
        references: [],
        timestamp: new Date(),
      }));
      setIsSending(false);
    }
  };

  const handleSend = async () => {
    if (!inputValue.trim() || isInputDisabled) return;
    const question = inputValue.trim();
    setInputValue("");

    const userMessage = createMessage("user", question);
    appendMessage(userMessage);
    setIsSending(true);

    const placeholderId = crypto.randomUUID();
    let placeholderAdded = false;

    const controller = new AbortController();
    let timeout: ReturnType<typeof setTimeout> | undefined;
    try {
      timeout = setTimeout(() => controller.abort(), 12000);
      const response: QueryResponse = await postQuery(question, controller.signal);
      const assistantMessage = createMessage("assistant", response.answer ?? "", response.references ?? []);
      appendMessage(assistantMessage);
      setIsSending(false);
    } catch (error) {
      if (isApiError(error)) {
        if (error.status === 500) {
          appendMessage(createMessage("error", `Sorry, an error occurred: ${error.message}`));
          setIsSending(false);
          return;
        }
        if (error.status && error.status < 500) {
          appendMessage(createMessage("error", `Sorry, an error occurred: ${error.message}`));
          setIsSending(false);
          return;
        }
      }

      if (!placeholderAdded) {
        placeholderAdded = true;
        appendMessage({
          id: placeholderId,
          type: "assistant",
          content: "Processing your question…",
          references: [],
          timestamp: new Date(),
        });
      }

      await handleAsyncFallback(question, placeholderId);
    } finally {
      if (timeout) {
        clearTimeout(timeout);
      }
    }
  };

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    void handleSend();
  };

  const messageGroups = useMemo(() => messages, [messages]);

  return (
    <div className="flex h-full flex-col bg-white">
      <header className="border-b border-zinc-200 px-6 py-4">
        <h2 className="text-lg font-semibold text-foreground">Chat</h2>
        <p className="text-sm text-muted-foreground">
          Ask questions about <span className="font-medium text-foreground">{documentName}</span> and review supporting references.
        </p>
      </header>

      <div className="flex-1 overflow-y-auto px-6 py-6">
        {messageGroups.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center text-sm text-muted-foreground">
            Start the conversation by asking a question about this document.
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            {messageGroups.map((message) => (
              <div
                key={message.id}
                className={
                  message.type === "user"
                    ? "ml-auto max-w-[70%] rounded-lg bg-primary text-primary-foreground px-4 py-3"
                    : message.type === "error"
                      ? "mr-auto max-w-[70%] rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-destructive"
                      : "mr-auto max-w-[70%] rounded-lg border border-zinc-200 bg-white px-4 py-3"
                }
              >
                <p className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</p>
                {message.references && message.references.length > 0 ? (
                  <div className="mt-3 flex flex-wrap gap-2 text-xs">
                    {message.references.map((reference, index) => (
                      <button
                        key={`${message.id}-ref-${index}`}
                        type="button"
                        className="rounded border border-primary/40 bg-primary/10 px-2 py-1 text-primary transition hover:bg-primary/20"
                        onClick={() => onReferenceClick(reference)}
                      >
                        Reference [{index + 1}]
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      <footer className="border-t border-zinc-200 px-6 py-4">
        {disabledReason ? (
          <div className="rounded-md border border-dashed border-zinc-200 bg-zinc-50 p-3 text-sm text-muted-foreground">
            {disabledReason}
          </div>
        ) : null}
        <form className="mt-3 flex items-end gap-3" onSubmit={handleSubmit}>
          <div className="flex-1">
            <textarea
              value={inputValue}
              onChange={(event) => setInputValue(event.target.value)}
              rows={2}
              disabled={isInputDisabled}
              placeholder="Ask a question about the processed document…"
              className="w-full resize-none rounded-md border border-zinc-200 bg-white px-3 py-2 text-sm shadow-sm focus-visible:border-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20 disabled:bg-zinc-100"
            />
          </div>
          <Button type="submit" disabled={isInputDisabled} className="inline-flex items-center gap-2">
            {isSending || pendingAsync ? <Loader2 className="h-4 w-4 animate-spin" /> : <SendHorizontal className="h-4 w-4" />}
            Send
          </Button>
        </form>
      </footer>
    </div>
  );
}
