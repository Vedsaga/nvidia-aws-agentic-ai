"use client";
import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { cn } from "@/lib/utils";

export type ToastVariant = "default" | "destructive";

export interface ToastPayload {
  id?: string;
  title?: string;
  description?: string;
  variant?: ToastVariant;
  duration?: number;
}

interface ToastContextValue {
  notify: (toast: ToastPayload) => void;
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

interface InternalToast extends ToastPayload {
  id: string;
  createdAt: number;
  duration: number;
}

function ToastContainer({ toasts, dismiss }: { toasts: InternalToast[]; dismiss: (id: string) => void }) {
  return (
    <div className="pointer-events-none fixed inset-x-0 top-4 z-[100] flex flex-col items-center gap-3 px-4 sm:items-end sm:px-6">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={cn(
            "pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-md border border-border bg-white p-4 shadow-lg transition-all", 
            toast.variant === "destructive" ? "border-destructive/40 bg-destructive/10" : "",
          )}
        >
          <div className="flex-1 space-y-1">
            {toast.title ? <p className="text-sm font-semibold text-foreground">{toast.title}</p> : null}
            {toast.description ? <p className="text-sm text-muted-foreground">{toast.description}</p> : null}
          </div>
          <button
            type="button"
            className="rounded px-2 py-1 text-xs font-medium text-muted-foreground hover:bg-muted"
            onClick={() => dismiss(toast.id)}
          >
            Close
          </button>
        </div>
      ))}
    </div>
  );
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<InternalToast[]>([]);

  useEffect(() => {
    if (!toasts.length) return;
    const timers = toasts.map((toast) =>
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== toast.id));
      }, toast.duration),
    );
    return () => {
      timers.forEach((timer) => clearTimeout(timer));
    };
  }, [toasts]);

  const dismiss = (id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  };

  const value = useMemo<ToastContextValue>(
    () => ({
      notify: (toast) => {
        setToasts((prev) => [
          ...prev,
          {
            id: toast.id ?? crypto.randomUUID(),
            createdAt: Date.now(),
            duration: toast.duration ?? 5000,
            title: toast.title,
            description: toast.description,
            variant: toast.variant ?? "default",
          },
        ]);
      },
    }),
    [],
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastContainer toasts={toasts} dismiss={dismiss} />
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}
