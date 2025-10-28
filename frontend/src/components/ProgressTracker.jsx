import { useState, useEffect, useRef } from 'react';
import { getIngestionStatus } from '../utils/api';

const ProgressTracker = ({ jobId, onComplete }) => {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);

  useEffect(() => {
    if (!jobId) {
      return;
    }

    const pollStatus = async () => {
      try {
        const data = await getIngestionStatus(jobId);
        setStatus(data);
        setError(null);

        if (data.status === 'completed' || data.status === 'failed') {
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
          if (onComplete) {
            onComplete(data);
          }
        }
      } catch (err) {
        setError(err.message || 'Failed to fetch status');
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      }
    };

    pollStatus();
    intervalRef.current = setInterval(pollStatus, 2000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [jobId, onComplete]);

  if (!jobId) {
    return null;
  }

  if (error) {
    return (
      <div className="progress-tracker error">
        <h3>Error</h3>
        <p>{error}</p>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="progress-tracker loading">
        <p>Loading status...</p>
      </div>
    );
  }

  const percentage = status.percentage || 0;
  const isComplete = status.status === 'completed';
  const isFailed = status.status === 'failed';

  return (
    <div className="progress-tracker">
      <h3>Processing Document</h3>
      
      <div className="progress-info">
        <span className="job-id">Job ID: {jobId}</span>
        <span className={`status ${status.status}`}>
          {status.status.toUpperCase()}
        </span>
      </div>

      <div className="progress-bar-container">
        <div 
          className="progress-bar" 
          style={{ width: `${percentage}%` }}
        />
      </div>
      
      <div className="progress-percentage">
        {percentage.toFixed(1)}%
      </div>

      {status.progress !== undefined && status.total !== undefined && (
        <div className="progress-details">
          <span>Processed: {status.progress} / {status.total} lines</span>
        </div>
      )}

      {status.statistics && (
        <div className="statistics">
          <div className="stat success">
            <span className="label">Success:</span>
            <span className="value">{status.statistics.success || 0}</span>
          </div>
          <div className="stat skipped">
            <span className="label">Skipped:</span>
            <span className="value">{status.statistics.skipped || 0}</span>
          </div>
          <div className="stat errors">
            <span className="label">Errors:</span>
            <span className="value">{status.statistics.errors || 0}</span>
          </div>
        </div>
      )}

      {isComplete && (
        <div className="completion-message success">
          ✓ Document processing completed successfully!
        </div>
      )}

      {isFailed && (
        <div className="completion-message failed">
          ✗ Document processing failed
        </div>
      )}
    </div>
  );
};

export default ProgressTracker;
