"use client";
import { useQuery } from "@tanstack/react-query";
import { getStatus } from "@/lib/api";
import type { JobStatus } from "@/lib/types";

export function useStatus(jobId: string | undefined, enabled: boolean = true) {
  const shouldEnable = Boolean(jobId) && enabled;
  return useQuery<JobStatus | null>({
    queryKey: ["status", jobId],
    queryFn: async () => {
      if (!jobId) return null;
      return await getStatus(jobId);
    },
    enabled: shouldEnable,
    refetchInterval: (query) => {
      const status = query.state.data?.status?.toLowerCase?.() ?? "unknown";
      if (status.includes("completed") || status.includes("failed")) {
        return false;
      }
      return 5000;
    },
    refetchOnWindowFocus: false,
  });
}
