'use client';

import { useState, useEffect } from 'react';
import { DocumentList } from '@/components/document-list';
import { DocumentStatus } from '@/components/document-status';
import { ChatInterface } from '@/components/chat-interface';
import { api, Job } from '@/lib/api';

export default function Home() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadJobs();
    const interval = setInterval(loadJobs, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadJobs = async () => {
    try {
      const data = await api.listDocs();
      setJobs(data);
      
      // Update selected job with latest status
      if (selectedJob) {
        const updated = data.find(j => j.job_id === selectedJob.job_id);
        if (updated && JSON.stringify(updated) !== JSON.stringify(selectedJob)) {
          setSelectedJob(updated);
        }
      }
    } catch (error) {
      console.error('Failed to load jobs:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (file: File) => {
    try {
      const { job_id } = await api.uploadFile(file);
      
      // Poll for the new job to appear
      for (let attempts = 0; attempts < 10; attempts++) {
        await new Promise(resolve => setTimeout(resolve, 1000));
        const data = await api.listDocs();
        setJobs(data);
        const newJob = data.find(j => j.job_id === job_id);
        if (newJob) {
          setSelectedJob(newJob);
          break;
        }
      }
    } catch (error) {
      console.error('Upload failed:', error);
      alert(`Upload failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  return (
    <div className="flex h-screen w-full">
      <DocumentList
        jobs={jobs}
        selectedJob={selectedJob}
        onSelectJob={setSelectedJob}
        onUpload={handleUpload}
        loading={loading}
      />
      {selectedJob && selectedJob.status === 'completed' ? (
        <ChatInterface job={selectedJob} />
      ) : selectedJob ? (
        <DocumentStatus job={selectedJob} />
      ) : (
        <div className="flex-1 flex items-center justify-center text-muted-foreground">
          Select a document to view details
        </div>
      )}
    </div>
  );
}
