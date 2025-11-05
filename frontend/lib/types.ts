export type DocumentStatusValue =
  | "pending"
  | "processing"
  | "uploading"
  | "queued"
  | "completed"
  | "failed"
  | "unknown";

export interface DocumentRecord {
  job_id: string;
  filename: string;
  status: string;
  created_at?: string;
  error_message?: string;
  failure_reason?: string;
  [key: string]: unknown;
}

export interface UploadInitResponse {
  job_id: string;
  pre_signed_url: string;
  [key: string]: unknown;
}

export interface JobStatus {
  job_id: string;
  filename?: string;
  status: string;
  total_sentences?: number;
  completed_sentences?: number;
  llm_calls_made?: number;
  progress_percentage?: number;
  failure_reason?: string;
  error_message?: string;
  last_updated_at?: string;
  [key: string]: unknown;
}

export interface ProcessingChainEntry {
  stage: string;
  timestamp: string;
  sentence_number?: number;
  duration_ms?: number;
  status?: string;
  message?: string;
  [key: string]: unknown;
}

export interface ProcessingChainResponse {
  job_id?: string;
  entries: ProcessingChainEntry[];
  [key: string]: unknown;
}

export interface ReferenceNode {
  id: string;
  label: string;
  node_type?: string;
  [key: string]: unknown;
}

export interface ReferenceEdge {
  source: string;
  target: string;
  label: string;
  [key: string]: unknown;
}

export interface ReferenceData {
  sentence_text: string;
  sentence_hash: string;
  kg_snippet: {
    nodes: ReferenceNode[];
    edges: ReferenceEdge[];
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

export interface QueryResponse {
  answer: string;
  references?: ReferenceData[];
  [key: string]: unknown;
}

export interface QueryStatusResponse {
  status: string;
  answer?: string;
  references?: ReferenceData[];
  error?: string;
  message?: string;
  [key: string]: unknown;
}

export interface SentenceChainStage {
  stage: string;
  timestamp: string;
  duration_ms?: number;
  status?: string;
  [key: string]: unknown;
}

export interface SentenceChainData {
  sentence_hash: string;
  processing_stages: SentenceChainStage[];
  [key: string]: unknown;
}

export type ChatMessageType = "user" | "assistant" | "error" | "system";

export interface ChatMessage {
  id: string;
  type: ChatMessageType;
  content: string;
  references?: ReferenceData[];
  timestamp: Date;
}

export class ApiError extends Error {
  status?: number;
  details?: unknown;
  payload?: unknown;
  isCanceled?: boolean;

  constructor(message: string, status?: number, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}
