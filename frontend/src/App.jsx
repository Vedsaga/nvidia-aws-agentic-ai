import { useState } from 'react'
import DocumentUpload from './components/DocumentUpload'

function App() {
  const [currentJobId, setCurrentJobId] = useState(null);
  const [currentDocumentId, setCurrentDocumentId] = useState(null);

  const handleUploadComplete = (jobId, documentId) => {
    setCurrentJobId(jobId);
    setCurrentDocumentId(documentId);
    console.log('Upload complete:', { jobId, documentId });
  };

  return (
    <div className="app">
      <h1>Kāraka Graph RAG System</h1>
      <p style={{ marginBottom: '2rem', color: '#666' }}>
        A semantic role-aware RAG system using Pāṇinian Kāraka semantics
      </p>
      
      <DocumentUpload onUploadComplete={handleUploadComplete} />
      
      {currentJobId && (
        <div style={{ marginTop: '1rem', padding: '1rem', background: '#f5f5f5', borderRadius: '6px' }}>
          <p><strong>Current Job:</strong> {currentJobId}</p>
          <p><strong>Document ID:</strong> {currentDocumentId}</p>
        </div>
      )}
    </div>
  )
}

export default App
