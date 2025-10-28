import { useState } from 'react';
import { Upload, FileText, AlertCircle, CheckCircle } from 'lucide-react';
import { ingestDocument } from '../utils/api';

const DocumentUpload = ({ onUploadComplete }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [error, setError] = useState(null);

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      if (file.type === 'text/plain' || file.name.endsWith('.txt')) {
        setSelectedFile(file);
        setError(null);
        setUploadStatus(null);
        setJobId(null);
      } else {
        setError('Please select a text file (.txt)');
        setSelectedFile(null);
      }
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select a file first');
      return;
    }

    setUploading(true);
    setError(null);
    setUploadStatus('reading');

    try {
      // Read file content
      const fileContent = await readFileAsText(selectedFile);
      
      setUploadStatus('uploading');
      
      // Convert to base64
      const base64Content = btoa(unescape(encodeURIComponent(fileContent)));
      
      // Call API
      const response = await ingestDocument(selectedFile.name, base64Content);
      
      setJobId(response.job_id);
      setUploadStatus('success');
      
      // Notify parent component
      if (onUploadComplete) {
        onUploadComplete(response.job_id, response.document_id);
      }
    } catch (err) {
      console.error('Upload error:', err);
      setError(err.response?.data?.error || err.message || 'Upload failed');
      setUploadStatus('error');
    } finally {
      setUploading(false);
    }
  };

  const readFileAsText = (file) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => resolve(e.target.result);
      reader.onerror = (e) => reject(new Error('Failed to read file'));
      reader.readAsText(file);
    });
  };

  const resetUpload = () => {
    setSelectedFile(null);
    setUploadStatus(null);
    setJobId(null);
    setError(null);
  };

  return (
    <div className="document-upload">
      <h2 className="section-title">
        <Upload size={20} />
        Upload Document
      </h2>
      
      <div className="upload-container">
        <div className="file-input-wrapper">
          <input
            type="file"
            id="file-input"
            accept=".txt,text/plain"
            onChange={handleFileSelect}
            disabled={uploading}
            className="file-input"
          />
          <label htmlFor="file-input" className="file-input-label">
            <FileText size={18} />
            {selectedFile ? selectedFile.name : 'Choose text file'}
          </label>
        </div>

        <button
          onClick={handleUpload}
          disabled={!selectedFile || uploading}
          className="upload-button"
        >
          {uploading ? 'Uploading...' : 'Upload'}
        </button>

        {uploadStatus === 'success' && (
          <button onClick={resetUpload} className="reset-button">
            Upload Another
          </button>
        )}
      </div>

      {uploadStatus === 'reading' && (
        <div className="status-message info">
          Reading file...
        </div>
      )}

      {uploadStatus === 'uploading' && (
        <div className="status-message info">
          Uploading document...
        </div>
      )}

      {uploadStatus === 'success' && jobId && (
        <div className="status-message success">
          <CheckCircle size={18} />
          <div>
            <div>Upload successful!</div>
            <div className="job-id">Job ID: {jobId}</div>
          </div>
        </div>
      )}

      {error && (
        <div className="status-message error">
          <AlertCircle size={18} />
          <div>{error}</div>
        </div>
      )}
    </div>
  );
};

export default DocumentUpload;
