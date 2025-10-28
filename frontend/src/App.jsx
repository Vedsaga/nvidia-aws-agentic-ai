import { useState } from 'react'
import DocumentUpload from './components/DocumentUpload'
import ProgressTracker from './components/ProgressTracker'

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
        <ProgressTracker 
          jobId={currentJobId} 
          onComplete={(status) => {
            console.log('Processing complete:', status);
          }}
        />
      )}
    </div>
  )
}

export default App
