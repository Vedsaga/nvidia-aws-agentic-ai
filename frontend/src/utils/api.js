import axios from 'axios';

const API_GATEWAY_URL = import.meta.env.VITE_API_GATEWAY_URL || '/api';

const apiClient = axios.create({
  baseURL: API_GATEWAY_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 300000, // 5 minutes for ingestion
});

export const ingestDocument = async (documentName, content) => {
  const response = await apiClient.post('/ingest', {
    document_name: documentName,
    content: content,
  });
  return response.data;
};

export const getIngestionStatus = async (jobId) => {
  const response = await apiClient.get(`/ingest/status/${jobId}`);
  return response.data;
};

export const queryGraph = async (question, minConfidence = 0.8, documentFilter = null) => {
  const response = await apiClient.post('/query', {
    question,
    min_confidence: minConfidence,
    document_filter: documentFilter,
  });
  return response.data;
};

export const getGraphVisualization = async () => {
  const response = await apiClient.get('/graph');
  return response.data;
};

export default apiClient;
