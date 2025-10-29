import { useState } from 'react'
import DocumentUpload from './components/DocumentUpload'
import ProgressTracker from './components/ProgressTracker'
import QueryInterface from './components/QueryInterface'
import GraphVisualization from './components/GraphVisualization'

function App() {
  const [currentJobId, setCurrentJobId] = useState(null);
  const [refreshGraph, setRefreshGraph] = useState(0);

  const handleUploadComplete = (jobId, documentId) => {
    setCurrentJobId(jobId);
    console.log('Upload complete:', { jobId, documentId });
  };

  const handleProcessingComplete = (status) => {
    console.log('Processing complete:', status);
    setRefreshGraph(prev => prev + 1);
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>Kāraka Graph RAG System</h1>
        <p>A semantic role-aware RAG system using Pāṇinian Kāraka semantics</p>
      </header>

      <div className="karaka-info">
        <h3>About Kāraka Semantic Roles</h3>
        <div className="karaka-grid">
          <div className="karaka-item">
            <span className="karaka-label karta">KARTA</span>
            <span className="karaka-desc">Agent - Who performs the action?</span>
          </div>
          <div className="karaka-item">
            <span className="karaka-label karma">KARMA</span>
            <span className="karaka-desc">Patient - What is acted upon?</span>
          </div>
          <div className="karaka-item">
            <span className="karaka-label karana">KARANA</span>
            <span className="karaka-desc">Instrument - By what means?</span>
          </div>
          <div className="karaka-item">
            <span className="karaka-label sampradana">SAMPRADANA</span>
            <span className="karaka-desc">Recipient - For whom? To whom?</span>
          </div>
          <div className="karaka-item">
            <span className="karaka-label adhikarana">ADHIKARANA</span>
            <span className="karaka-desc">Location - Where?</span>
          </div>
          <div className="karaka-item">
            <span className="karaka-label apadana">APADANA</span>
            <span className="karaka-desc">Source - From where?</span>
          </div>
        </div>
      </div>

      <div className="main-layout">
        <div className="left-panel">
          <DocumentUpload onUploadComplete={handleUploadComplete} />
          
          {currentJobId && (
            <ProgressTracker 
              jobId={currentJobId} 
              onComplete={handleProcessingComplete}
            />
          )}
          
          <QueryInterface />
        </div>

        <div className="right-panel">
          <GraphVisualization key={refreshGraph} />
        </div>
      </div>
    </div>
  )
}

export default App
