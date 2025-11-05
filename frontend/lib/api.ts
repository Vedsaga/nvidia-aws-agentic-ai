import axios from "axios";
import {
  ApiError,
  DocumentRecord,
  JobStatus,
  ProcessingChainEntry,
  ProcessingChainResponse,
  QueryResponse,
  QueryStatusResponse,
  ReferenceData,
  SentenceChainData,
  UploadInitResponse,
} from "./types";

function sanitizeBaseUrl(value?: string) {
  if (!value) {
    return undefined;
  }
  const trimmed = value.trim();
  if (!trimmed || trimmed.includes("your-api-gateway-url")) {
    return undefined;
  }
  return trimmed;
}

function resolveBaseUrl() {
  const explicit = sanitizeBaseUrl(process.env.NEXT_PUBLIC_API_URL);
  if (explicit) {
    return explicit;
  }
  const shared = sanitizeBaseUrl(process.env.APP_API_GATEWAY_URL);
  if (shared) {
    return shared;
  }
  if (process.env.NODE_ENV === "development") {
    console.warn("API base URL is not configured; falling back to relative routes");
  }
  return "";
}

const baseURL = resolveBaseUrl();

export const apiClient = axios.create({
  baseURL,
  headers: { "Content-Type": "application/json" },
  timeout: 15000,
});

// Provide runtime visibility for debugging and avoid accidentally sending
// requests to the placeholder host. If no valid base URL is configured,
// requests will use relative URLs so the browser's origin is used.
export const resolvedApiBaseUrl = baseURL;

apiClient.interceptors.request.use((config) => {
  if (!baseURL || baseURL.includes("your-api-gateway-url")) {
    if (process.env.NODE_ENV === "development") {
      // eslint-disable-next-line no-console
      console.warn(
        "API client: no valid base URL configured (NEXT_PUBLIC_API_URL or APP_API_GATEWAY_URL). Using relative requests."
      );
    }
    // Ensure axios does not attempt to resolve the placeholder host
    // and instead sends requests relative to the current origin.
    return { ...config, baseURL: "" };
  }
  return config;
});

function unwrapDynamoValue(value: unknown): unknown {
  if (value == null) return value;
  if (typeof value !== "object") return value;
  const v = value as Record<string, unknown>;
  if ("S" in v && typeof v.S === "string") return v.S;
  if ("N" in v && (typeof v.N === "string" || typeof v.N === "number")) return Number(String(v.N));
  if ("BOOL" in v) return Boolean((v.BOOL as unknown) as boolean);
  if ("M" in v && v.M && typeof v.M === "object") {
    return normalizeDynamoItem(v.M as Record<string, unknown>);
  }
  if ("L" in v && Array.isArray(v.L)) {
    return v.L.map((item) => unwrapDynamoValue(item));
  }
  return value;
}

function normalizeDynamoItem(item: Record<string, unknown>): Record<string, unknown> {
  const output: Record<string, unknown> = {};
  for (const key of Object.keys(item || {})) {
    output[key] = unwrapDynamoValue(item[key]);
  }
  return output;
}

function ensureDocumentRecord(entry: unknown): DocumentRecord {
  if (!entry || typeof entry !== "object") {
    throw new ApiError("Invalid document payload received from API");
  }
  const e = entry as Record<string, unknown>;
  const normalized = "job_id" in e || "status" in e ? e : normalizeDynamoItem(e as Record<string, unknown>);
  const jobId = (normalized.job_id as string) || (normalized.jobId as string);
  if (!jobId || typeof jobId !== "string") {
    throw new ApiError("Document missing job_id field");
  }
  return {
    ...normalized,
    job_id: jobId,
    filename: (normalized.filename as string) || (normalized.file_name as string) || (normalized.name as string) || "(unnamed)",
    status: (normalized.status as string) || (normalized.document_status as string) || "unknown",
  } as DocumentRecord;
}

function normalizeProcessingEntry(entry: unknown): ProcessingChainEntry {
  if (!entry || typeof entry !== "object") {
    return {
      stage: "Unknown",
      timestamp: new Date().toISOString(),
    };
  }
  const normalized = normalizeDynamoItem(entry as Record<string, unknown>);
  return {
    ...normalized,
    stage: (normalized.stage as string) || (normalized.Stage as string) || "Unknown",
    timestamp: (normalized.timestamp as string) || (normalized.Timestamp as string) || new Date().toISOString(),
    status: (normalized.status as string) || (normalized.Status as string),
    sentence_number: (normalized.sentence_number as number) || (normalized.sentenceNumber as number),
    duration_ms: (normalized.duration_ms as number) || (normalized.durationMs as number),
  } as ProcessingChainEntry;
}

function toApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const axiosError = error as {
      response?: { status?: number; data?: unknown };
      message?: string;
      code?: string;
    };
    const status = axiosError.response?.status;
    const payload = axiosError.response?.data;
    const payloadRec = payload as Record<string, unknown> | undefined;
    const message =
      (payloadRec && typeof payloadRec.message === "string" && payloadRec.message) ||
      (payloadRec && typeof payloadRec.error === "string" && (payloadRec.error as string)) ||
      (typeof payload === "string" ? payload : undefined) ||
      axiosError.message ||
      "Request failed";
    const apiError = new ApiError(message, status, payload);
    apiError.payload = payload;
    apiError.isCanceled = axiosError.code === "ERR_CANCELED";
    return apiError;
  }
  if (error instanceof ApiError) {
    return error;
  }
  if (error instanceof Error) {
    return new ApiError(error.message);
  }
  return new ApiError("Unknown error");
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

export async function getDocs(): Promise<DocumentRecord[]> {
  try {
    const res = await apiClient.get("/docs");
    const payload = res.data;
    const collection =
      (Array.isArray(payload) ? payload : undefined) ||
      (Array.isArray(payload?.data) ? payload.data : undefined) ||
      (Array.isArray(payload?.documents) ? payload.documents : undefined) ||
      (Array.isArray(payload?.Items) ? payload.Items : undefined) ||
      [];
    return collection.map(ensureDocumentRecord);
  } catch (error) {
    throw toApiError(error);
  }
}

export async function createUpload(filename: string): Promise<UploadInitResponse> {
  try {
    const res = await apiClient.post("/upload", { filename });
    const data = res.data || {};
    const jobId = data.job_id || data.jobId;
    const url = data.pre_signed_url || data.preSignedUrl || data.presigned_url;
    if (!jobId || !url) {
      throw new ApiError("Upload endpoint did not return job_id or pre_signed_url");
    }
    return {
      ...data,
      job_id: jobId,
      pre_signed_url: url,
    } as UploadInitResponse;
  } catch (error) {
    throw toApiError(error);
  }
}

export async function uploadToPresignedUrl(url: string, file: File | Blob): Promise<void> {
  try {
    const res = await fetch(url, {
      method: "PUT",
      body: file,
    });
    if (!res.ok) {
      throw new ApiError(`File upload failed with status ${res.status}`);
    }
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(error instanceof Error ? error.message : "File upload failed");
  }
}

export async function triggerProcessing(jobId: string) {
  try {
    const res = await apiClient.post(`/trigger/${jobId}`);
    return res.data;
  } catch (error) {
    throw toApiError(error);
  }
}

export async function getStatus(jobId: string): Promise<JobStatus> {
  try {
    const res = await apiClient.get(`/status/${jobId}`);
    const data = res.data || {};
    return {
      ...data,
      job_id: data.job_id || data.jobId || jobId,
      status: data.status || data.document_status || "unknown",
      filename: data.filename || data.file_name,
    } as JobStatus;
  } catch (error) {
    throw toApiError(error);
  }
}

export async function getProcessingChain(jobId: string): Promise<ProcessingChainResponse> {
  try {
    const res = await apiClient.get(`/processing-chain/${jobId}`);
    const data = res.data || {};
    const entriesRaw = Array.isArray(data)
      ? data
      : Array.isArray(data.entries)
        ? data.entries
        : Array.isArray(data.data)
          ? data.data
          : [];
    const entries = entriesRaw.map(normalizeProcessingEntry);
    return {
      ...data,
      job_id: data.job_id || data.jobId || jobId,
      entries,
    } as ProcessingChainResponse;
  } catch (error) {
    throw toApiError(error);
  }
}

export async function postQuery(query: string, signal?: AbortSignal): Promise<QueryResponse> {
  try {
    const res = await apiClient.post(
      `/query`,
      { query },
      {
        signal,
      },
    );
    return res.data as QueryResponse;
  } catch (error) {
    throw toApiError(error);
  }
}

export async function postQuerySubmit(question: string): Promise<{ query_id: string; [key: string]: unknown }> {
  try {
    const res = await apiClient.post(`/query/submit`, { question });
    const data = res.data || {};
    const queryId = data.query_id || data.queryId;
    if (!queryId) {
      throw new ApiError("Async query submission did not return query_id");
    }
    return {
      ...data,
      query_id: queryId,
    };
  } catch (error) {
    throw toApiError(error);
  }
}

export async function getQueryStatus(queryId: string): Promise<QueryStatusResponse> {
  try {
    const res = await apiClient.get(`/query/status/${queryId}`);
    const data = res.data || {};
    return {
      ...data,
      references: Array.isArray(data.references) ? (data.references as ReferenceData[]) : undefined,
    } as QueryStatusResponse;
  } catch (error) {
    throw toApiError(error);
  }
}

export async function getSentenceChain(sentenceHash: string): Promise<SentenceChainData> {
  try {
    const res = await apiClient.get(`/sentence-chain/${sentenceHash}`);
    const data = res.data || {};
    const stages = Array.isArray(data.processing_stages)
      ? data.processing_stages
      : Array.isArray(data.data)
        ? data.data
        : [];
    return {
      ...data,
      sentence_hash: data.sentence_hash || data.sentenceHash || sentenceHash,
      processing_stages: stages,
    } as SentenceChainData;
  } catch (error) {
    throw toApiError(error);
  }
}

export { normalizeDynamoItem };
