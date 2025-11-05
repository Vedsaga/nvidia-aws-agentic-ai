"use client";
import { useQuery } from "@tanstack/react-query";
import { getProcessingChain } from "@/lib/api";
import type { ProcessingChainResponse } from "@/lib/types";

export function useProcessingChain(jobId: string | undefined, enabled: boolean = true) {
  const shouldEnable = Boolean(jobId) && enabled;
  return useQuery<ProcessingChainResponse>({
    queryKey: ["processing-chain", jobId],
    queryFn: async () => {
      if (!jobId) {
        return { entries: [] } as ProcessingChainResponse;
      }
      return await getProcessingChain(jobId);
    },
    enabled: shouldEnable,
    refetchInterval: 5000,
    refetchOnWindowFocus: false,
    retry: (failureCount, error) => {
      const status = (error as any)?.status;
      if (status === 502) {
        return false;
      }
      return failureCount < 3;
    },
  });
}
