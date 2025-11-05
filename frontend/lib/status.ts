import type { DocumentStatusValue } from "@/lib/types";

const PROCESSING_KEYWORDS = ["processing", "running", "in_progress", "processing_kg", "queued"];
const FAILED_KEYWORDS = ["failed", "error", "stopped"];
const COMPLETED_KEYWORDS = ["completed", "succeeded", "done", "finished"];

export function deriveDocumentStatus(rawStatus?: string): DocumentStatusValue {
  if (!rawStatus) return "unknown";
  const status = String(rawStatus).toLowerCase();
  if (COMPLETED_KEYWORDS.some((keyword) => status.includes(keyword))) return "completed";
  if (FAILED_KEYWORDS.some((keyword) => status.includes(keyword))) return "failed";
  if (PROCESSING_KEYWORDS.some((keyword) => status.includes(keyword))) return "processing";
  if (status.includes("upload")) return "uploading";
  if (status.includes("pending")) return "pending";
  return "unknown";
}

export function formatStatusLabel(rawStatus?: string): string {
  if (!rawStatus) return "Unknown";
  return rawStatus
    .replace(/_/g, " ")
    .replace(/\b\w/g, (match) => match.toUpperCase());
}
