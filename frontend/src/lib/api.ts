const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://7g3bdwsnsc.execute-api.us-east-1.amazonaws.com/prod';

export interface Job {
  job_id: string;
  filename: string;
  status: string;
  total_sentences: number;
  completed_sentences: number;
  llm_calls_made: number;
  created_at: string;
  progress_percentage: number;
}

export interface Query {
  query_id: string;
  question: string;
  status: string;
  answer?: string;
  references?: Array<{
    sentence: string;
    source: string;
  }>;
}

export interface ProcessingChainEntry {
  stage: string;
  timestamp: number;
  duration_ms: number;
}

export const api = {
  async uploadFile(file: File): Promise<{ job_id: string; pre_signed_url: string }> {
    const res = await fetch(`${API_URL}/upload`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename: file.name }),
    });
    
    if (!res.ok) {
      throw new Error(`Upload request failed: ${res.statusText}`);
    }
    
    const data = await res.json();
    
    // Upload file to S3 using pre-signed URL
    const uploadRes = await fetch(data.pre_signed_url, {
      method: 'PUT',
      body: file,
      headers: { 'Content-Type': 'text/plain' },
    });
    
    if (!uploadRes.ok) {
      throw new Error(`S3 upload failed: ${uploadRes.statusText}`);
    }
    
    return data;
  },

  async getJobStatus(jobId: string): Promise<Job> {
    const res = await fetch(`${API_URL}/status/${jobId}`);
    if (!res.ok) {
      throw new Error(`Failed to get job status: ${res.statusText}`);
    }
    return res.json();
  },

  async listDocs(): Promise<Job[]> {
    const res = await fetch(`${API_URL}/docs`);
    if (!res.ok) {
      throw new Error(`Failed to list docs: ${res.statusText}`);
    }
    const data = await res.json();
    return Array.isArray(data) ? data : [];
  },

  async submitQuery(question: string, jobId?: string): Promise<{ query_id: string }> {
    const body: any = { question };
    if (jobId) body.job_id = jobId;
    
    const res = await fetch(`${API_URL}/query/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    
    if (!res.ok) {
      throw new Error(`Failed to submit query: ${res.statusText}`);
    }
    return res.json();
  },

  async getQueryStatus(queryId: string): Promise<Query> {
    const res = await fetch(`${API_URL}/query/status/${queryId}`);
    if (!res.ok) {
      throw new Error(`Failed to get query status: ${res.statusText}`);
    }
    return res.json();
  },

  async getProcessingChain(jobId: string): Promise<ProcessingChainEntry[]> {
    try {
      const res = await fetch(`${API_URL}/processing-chain/${jobId}`);
      if (!res.ok) return [];
      const data = await res.json();
      return Array.isArray(data) ? data : [];
    } catch (error) {
      console.error('Failed to get processing chain:', error);
      return [];
    }
  },
};
