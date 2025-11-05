"use client";
import { useQuery } from "@tanstack/react-query";
import { getDocs } from "@/lib/api";
import type { DocumentRecord } from "@/lib/types";

export function useDocuments() {
  return useQuery<DocumentRecord[]>({
    queryKey: ["documents"],
    queryFn: getDocs,
    refetchInterval: 15000,
    staleTime: 5000,
    refetchOnWindowFocus: false,
  });
}
