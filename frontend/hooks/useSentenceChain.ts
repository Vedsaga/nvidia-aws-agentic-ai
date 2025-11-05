"use client";
import { useQuery } from "@tanstack/react-query";
import { getSentenceChain } from "@/lib/api";
import type { SentenceChainData } from "@/lib/types";

export function useSentenceChain(sentenceHash: string | undefined) {
  const enabled = Boolean(sentenceHash);
  return useQuery<SentenceChainData | null>({
    queryKey: ["sentence-chain", sentenceHash],
    queryFn: async () => {
      if (!sentenceHash) return null;
      return await getSentenceChain(sentenceHash);
    },
    enabled,
    retry: 1,
    refetchOnWindowFocus: false,
  });
}
