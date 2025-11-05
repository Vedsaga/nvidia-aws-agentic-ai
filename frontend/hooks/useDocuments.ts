"use client";
import { useQuery } from "@tanstack/react-query";
import { getDocs } from "@/lib/api";
import type { DocumentRecord } from "@/lib/types";

export function useDocuments() {
  return useQuery<DocumentRecord[]>({
    queryKey: ["documents"],
    queryFn: getDocs,
    // Do not poll /docs automatically. Fetch once on page load; the user
    // can manually refresh via the UI refresh button which calls
    // `documentsQuery.refetch()`.
    refetchInterval: false,
    staleTime: 5000,
    refetchOnWindowFocus: false,
  });
}
